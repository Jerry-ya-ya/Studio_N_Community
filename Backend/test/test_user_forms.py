from datetime import timedelta
from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token

from models import FormSubmission, FormTemplate, User, db
from time_utils import taipei_now


@pytest.fixture()
def survey_records(app):
    suffix = uuid4().hex
    with app.app_context():
        admin = User(
            username=f'survey-admin-{suffix}',
            email=f'survey-admin-{suffix}@example.com',
            password='test-password',
            role='admin',
            email_verified=True,
        )
        member = User(
            username=f'survey-user-{suffix}',
            email=f'survey-user-{suffix}@example.com',
            password='test-password',
            role='user',
            email_verified=True,
        )
        db.session.add_all([admin, member])
        db.session.flush()
        form = FormTemplate(
            title='Developer survey',
            description='Tell us about your work.',
            definition={
                'schemaVersion': 1,
                'questions': [
                    {
                        'id': 'name', 'type': 'short_text', 'title': 'Name',
                        'description': '', 'required': True, 'options': [],
                    },
                    {
                        'id': 'notes', 'type': 'long_text', 'title': 'Notes',
                        'description': '', 'required': False, 'options': [],
                    },
                    {
                        'id': 'track', 'type': 'single_choice', 'title': 'Track',
                        'description': '', 'required': True,
                        'options': [
                            {'id': 'frontend', 'label': 'Frontend'},
                            {'id': 'backend', 'label': 'Backend'},
                        ],
                    },
                    {
                        'id': 'tools', 'type': 'multiple_choice', 'title': 'Tools',
                        'description': '', 'required': False,
                        'options': [
                            {'id': 'git', 'label': 'Git'},
                            {'id': 'docker', 'label': 'Docker'},
                        ],
                    },
                    {
                        'id': 'level', 'type': 'dropdown', 'title': 'Level',
                        'description': '', 'required': False,
                        'options': [
                            {'id': 'junior', 'label': 'Junior'},
                            {'id': 'senior', 'label': 'Senior'},
                        ],
                    },
                    {
                        'id': 'years', 'type': 'number', 'title': 'Years',
                        'description': '', 'required': False, 'options': [],
                    },
                    {
                        'id': 'start', 'type': 'date', 'title': 'Start date',
                        'description': '', 'required': False, 'options': [],
                    },
                    {
                        'id': 'remote', 'type': 'boolean', 'title': 'Remote',
                        'description': '', 'required': True, 'options': [],
                    },
                ],
            },
            created_by_id=admin.id,
        )
        db.session.add(form)
        db.session.commit()
        result = {
            'form_id': form.id,
            'admin_id': admin.id,
            'member_id': member.id,
            'token': create_access_token(identity=str(member.id)),
        }

    yield result

    with app.app_context():
        FormSubmission.query.filter_by(user_id=result['member_id']).delete()
        FormTemplate.query.filter_by(id=result['form_id']).delete()
        User.query.filter(User.id.in_([result['admin_id'], result['member_id']])).delete(
            synchronize_session=False
        )
        db.session.commit()


def bearer(token):
    return {'Authorization': f'Bearer {token}'}


def valid_submission(version=1):
    return {
        'formVersion': version,
        'answers': {
            'name': '  Ada  ',
            'notes': '',
            'track': 'backend',
            'tools': ['git', 'docker'],
            'level': 'senior',
            'years': 5,
            'start': '2026-09-13',
            'remote': False,
        },
    }


def test_user_form_endpoints_require_authentication(client, survey_records):
    assert client.get('/api/forms').status_code == 401
    assert client.post(
        f"/api/forms/{survey_records['form_id']}/submissions",
        json=valid_submission(),
    ).status_code == 401


def test_user_can_list_and_submit_a_form(client, app, survey_records):
    headers = bearer(survey_records['token'])
    list_response = client.get('/api/forms', headers=headers)

    assert list_response.status_code == 200
    assert list_response.headers['Cache-Control'] == 'no-store'
    listed = next(
        form for form in list_response.get_json()
        if form['id'] == survey_records['form_id']
    )
    assert listed['submitted'] is False
    assert listed['submittedAt'] is None
    assert 'created_by_id' not in listed

    response = client.post(
        f"/api/forms/{survey_records['form_id']}/submissions",
        headers=headers,
        json=valid_submission(),
    )
    assert response.status_code == 201
    assert response.get_json()['formVersion'] == 1

    with app.app_context():
        stored = FormSubmission.query.filter_by(
            form_id=survey_records['form_id'], user_id=survey_records['member_id']
        ).one()
        assert stored.answers['name'] == 'Ada'
        assert stored.answers['notes'] is None
        assert stored.answers['remote'] is False
        assert stored.form_snapshot['title'] == 'Developer survey'
        assert stored.form_snapshot['schema']['questions'][0]['id'] == 'name'

    listed = next(
        form for form in client.get('/api/forms', headers=headers).get_json()
        if form['id'] == survey_records['form_id']
    )
    assert listed['submitted'] is True
    assert listed['submittedAt']


def test_submission_rejects_missing_and_invalid_answers(client, survey_records):
    headers = bearer(survey_records['token'])
    endpoint = f"/api/forms/{survey_records['form_id']}/submissions"

    payload = valid_submission()
    payload['answers']['name'] = ''
    response = client.post(endpoint, headers=headers, json=payload)
    assert response.status_code == 400
    assert response.get_json()['field'] == 'answers.name'

    payload = valid_submission()
    payload['answers']['track'] = 'unknown'
    response = client.post(endpoint, headers=headers, json=payload)
    assert response.status_code == 400
    assert response.get_json()['field'] == 'answers.track'

    payload = valid_submission()
    payload['answers']['tools'] = ['git', 'git']
    assert client.post(endpoint, headers=headers, json=payload).status_code == 400

    payload = valid_submission()
    payload['answers']['start'] = '09/13/2026'
    assert client.post(endpoint, headers=headers, json=payload).status_code == 400

    payload = valid_submission()
    payload['answers']['remote'] = 'false'
    assert client.post(endpoint, headers=headers, json=payload).status_code == 400

    payload = valid_submission()
    payload['answers']['unknown'] = 'answer'
    response = client.post(endpoint, headers=headers, json=payload)
    assert response.status_code == 400
    assert response.get_json()['field'] == 'answers'


def test_submission_is_once_per_user_and_form_version(client, app, survey_records):
    headers = bearer(survey_records['token'])
    endpoint = f"/api/forms/{survey_records['form_id']}/submissions"
    assert client.post(endpoint, headers=headers, json=valid_submission()).status_code == 201

    duplicate = client.post(endpoint, headers=headers, json=valid_submission())
    assert duplicate.status_code == 409
    assert duplicate.get_json()['code'] == 'already_submitted'

    with app.app_context():
        form = db.session.get(FormTemplate, survey_records['form_id'])
        form.version = 2
        form.title = 'Updated developer survey'
        db.session.commit()

    stale = client.post(endpoint, headers=headers, json=valid_submission(1))
    assert stale.status_code == 409
    assert stale.get_json()['code'] == 'version_conflict'

    current = client.post(endpoint, headers=headers, json=valid_submission(2))
    assert current.status_code == 201

    with app.app_context():
        submissions = FormSubmission.query.filter_by(
            form_id=survey_records['form_id'], user_id=survey_records['member_id']
        ).order_by(FormSubmission.form_version).all()
        assert [submission.form_version for submission in submissions] == [1, 2]
        assert submissions[0].form_snapshot['title'] == 'Developer survey'
        assert submissions[1].form_snapshot['title'] == 'Updated developer survey'


def test_submission_requires_json_and_limits_payload(client, survey_records):
    endpoint = f"/api/forms/{survey_records['form_id']}/submissions"
    headers = bearer(survey_records['token'])
    response = client.post(endpoint, headers=headers, data='not-json')
    assert response.status_code == 415

    response = client.post(
        endpoint,
        headers={**headers, 'Content-Type': 'application/json'},
        data='{' + (' ' * (128 * 1024)) + '}',
    )
    assert response.status_code == 413


@pytest.mark.parametrize('manual_settlement', [False, True])
def test_settled_form_rejects_submissions(
    client, app, survey_records, manual_settlement
):
    with app.app_context():
        form = db.session.get(FormTemplate, survey_records['form_id'])
        if manual_settlement:
            form.settled_at = taipei_now()
        else:
            form.settlement_at = taipei_now() - timedelta(minutes=1)
        db.session.commit()

    response = client.post(
        f"/api/forms/{survey_records['form_id']}/submissions",
        headers=bearer(survey_records['token']),
        json=valid_submission(),
    )

    assert response.status_code == 409
    assert response.get_json()['code'] == 'form_settled'
