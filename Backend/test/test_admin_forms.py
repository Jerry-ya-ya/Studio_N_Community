from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token

from models import FormTemplate, User, db
from routes.admin.forms import MAX_OPTIONS, MAX_QUESTIONS, normalize_form_payload


@pytest.fixture()
def form_accounts(app):
    suffix = uuid4().hex
    with app.app_context():
        admin = User(
            username=f'form-admin-{suffix}',
            email=f'form-admin-{suffix}@example.com',
            password='test-password',
            role='admin',
            email_verified=True,
        )
        member = User(
            username=f'form-member-{suffix}',
            email=f'form-member-{suffix}@example.com',
            password='test-password',
            role='user',
            email_verified=True,
        )
        db.session.add_all([admin, member])
        db.session.commit()
        result = {
            'admin_id': admin.id,
            'admin_token': create_access_token(identity=str(admin.id)),
            'member_id': member.id,
            'member_token': create_access_token(identity=str(member.id)),
        }

    yield result

    with app.app_context():
        FormTemplate.query.filter_by(created_by_id=result['admin_id']).delete()
        User.query.filter(User.id.in_([result['admin_id'], result['member_id']])).delete(
            synchronize_session=False
        )
        db.session.commit()


def bearer(token):
    return {'Authorization': f'Bearer {token}'}


def valid_payload():
    return {
        'title': 'Registration form',
        'description': 'Please complete every required field.',
        'schema': {
            'schemaVersion': 1,
            'questions': [
                {
                    'id': 'q_name',
                    'type': 'short_text',
                    'title': 'Your name',
                    'description': '',
                    'required': True,
                    'options': [],
                },
                {
                    'id': 'q_track',
                    'type': 'single_choice',
                    'title': 'Choose a track',
                    'description': 'Pick one.',
                    'required': False,
                    'options': [
                        {'id': 'o_frontend', 'label': 'Frontend'},
                        {'id': 'o_backend', 'label': 'Backend'},
                    ],
                },
            ],
        },
    }


def test_form_endpoints_require_admin(client, form_accounts):
    assert client.get('/api/admin/forms').status_code == 401
    response = client.get(
        '/api/admin/forms', headers=bearer(form_accounts['member_token'])
    )
    assert response.status_code == 403
    assert response.get_json() == {'error': '需要管理員權限'}


def test_form_crud_persists_normalized_json_schema(client, app, form_accounts):
    headers = bearer(form_accounts['admin_token'])
    payload = valid_payload()
    payload['title'] = '  Registration form  '
    created_response = client.post('/api/admin/forms', headers=headers, json=payload)

    assert created_response.status_code == 201
    created = created_response.get_json()
    form_id = created['id']
    assert created['title'] == 'Registration form'
    assert created['version'] == 1
    assert created['created_by_id'] == form_accounts['admin_id']
    assert created['schema']['schemaVersion'] == 1
    assert created['schema']['questions'][1]['options'][0]['label'] == 'Frontend'

    list_response = client.get('/api/admin/forms', headers=headers)
    assert list_response.status_code == 200
    assert list_response.headers['Cache-Control'] == 'no-store'
    assert form_id in [form['id'] for form in list_response.get_json()]

    detail_response = client.get(f'/api/admin/forms/{form_id}', headers=headers)
    assert detail_response.status_code == 200
    assert detail_response.headers['Cache-Control'] == 'no-store'

    update_payload = valid_payload()
    update_payload.update({'title': 'Updated form', 'version': created['version']})
    updated_response = client.put(
        f'/api/admin/forms/{form_id}', headers=headers, json=update_payload
    )
    assert updated_response.status_code == 200
    updated = updated_response.get_json()
    assert updated['title'] == 'Updated form'
    assert updated['version'] == 2

    with app.app_context():
        stored = db.session.get(FormTemplate, form_id)
        assert stored.definition == updated['schema']

    deleted_response = client.delete(f'/api/admin/forms/{form_id}', headers=headers)
    assert deleted_response.status_code == 200
    assert deleted_response.get_json() == {'message': 'form deleted', 'id': form_id}
    with app.app_context():
        assert db.session.get(FormTemplate, form_id) is None


def test_update_rejects_stale_version(client, form_accounts):
    headers = bearer(form_accounts['admin_token'])
    created = client.post(
        '/api/admin/forms', headers=headers, json=valid_payload()
    ).get_json()
    payload = valid_payload()
    payload['version'] = created['version'] + 1

    response = client.put(
        f"/api/admin/forms/{created['id']}", headers=headers, json=payload
    )

    assert response.status_code == 409
    assert response.get_json()['code'] == 'version_conflict'
    assert response.get_json()['currentVersion'] == 1


@pytest.mark.parametrize(
    ('change', 'expected_field'),
    [
        ({'unexpected': True}, None),
        ({'version': 1}, None),
        ({'title': ''}, 'title'),
        ({'title': 'x' * 121}, 'title'),
        ({'schema': []}, 'schema'),
        ({'schema': {'schemaVersion': 2, 'questions': []}}, 'schema.schemaVersion'),
        ({'schema': {'schemaVersion': True, 'questions': []}}, 'schema.schemaVersion'),
        ({'schema': {'schemaVersion': 1, 'questions': {}}}, 'schema.questions'),
    ],
)
def test_form_payload_rejects_unsupported_or_malformed_data(change, expected_field):
    payload = valid_payload()
    payload.update(change)

    normalized, error = normalize_form_payload(payload)

    assert normalized is None
    body, status = error
    assert status == 400
    assert body['code'] == 'invalid_form'
    if expected_field:
        assert body['field'] == expected_field


@pytest.mark.parametrize(
    'question_change',
    [
        {'type': 'script'},
        {'title': ''},
        {'required': 'yes'},
        {'id': '<unsafe>'},
        {'extra': 'field'},
        {'type': 'single_choice', 'options': [{'id': 'one', 'label': 'Only'}]},
        {
            'type': 'short_text',
            'options': [
                {'id': 'one', 'label': 'Unexpected'},
                {'id': 'two', 'label': 'Unexpected'},
            ],
        },
    ],
)
def test_form_payload_rejects_unsafe_questions(question_change):
    payload = valid_payload()
    payload['schema']['questions'][0].update(question_change)

    normalized, error = normalize_form_payload(payload)

    assert normalized is None
    assert error[1] == 400


def test_form_payload_enforces_collection_limits():
    payload = valid_payload()
    payload['schema']['questions'] = [
        {
            'id': f'q_{index}',
            'type': 'short_text',
            'title': 'Question',
            'description': '',
            'required': False,
            'options': [],
        }
        for index in range(MAX_QUESTIONS + 1)
    ]
    assert normalize_form_payload(payload)[0] is None

    payload = valid_payload()
    payload['schema']['questions'][1]['options'] = [
        {'id': f'o_{index}', 'label': 'Option'}
        for index in range(MAX_OPTIONS + 1)
    ]
    assert normalize_form_payload(payload)[0] is None


def test_form_endpoint_requires_json_and_limits_body_size(client, form_accounts):
    headers = bearer(form_accounts['admin_token'])
    response = client.post('/api/admin/forms', headers=headers, data='not json')
    assert response.status_code == 415
    assert response.get_json()['code'] == 'unsupported_media_type'

    response = client.post(
        '/api/admin/forms',
        headers={**headers, 'Content-Type': 'application/json'},
        data='{' + (' ' * (128 * 1024)) + '}',
    )
    assert response.status_code == 413
    assert response.get_json()['code'] == 'payload_too_large'


def test_form_missing_resources_return_json_404(client, form_accounts):
    headers = bearer(form_accounts['admin_token'])
    assert client.get('/api/admin/forms/999999', headers=headers).status_code == 404
    assert client.put(
        '/api/admin/forms/999999', headers=headers, json={}
    ).get_json()['code'] == 'not_found'
    assert client.delete(
        '/api/admin/forms/999999', headers=headers
    ).get_json()['code'] == 'not_found'
