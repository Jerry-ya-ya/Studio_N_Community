from copy import deepcopy
from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token

from models import FormSubmission, FormTemplate, User, db
from time_utils import taipei_now


@pytest.fixture()
def statistics_data(app):
    suffix = uuid4().hex
    with app.app_context():
        superadmin = User(
            username=f'stats-root-{suffix}', email=f'stats-root-{suffix}@example.com',
            password='test-password', role='superadmin', email_verified=True,
        )
        admin = User(
            username=f'stats-admin-{suffix}', email=f'stats-admin-{suffix}@example.com',
            password='test-password', role='admin', email_verified=True,
        )
        member = User(
            username=f'stats-member-{suffix}', email=f'stats-member-{suffix}@example.com',
            password='test-password', role='user', email_verified=True,
        )
        db.session.add_all([superadmin, admin, member])
        db.session.flush()
        schema = {
            'schemaVersion': 1,
            'questions': [
                {'id': 'track', 'type': 'single_choice', 'title': 'Track',
                 'description': '', 'required': True,
                 'options': [{'id': 'web', 'label': 'Web'}, {'id': 'game', 'label': 'Game'}]},
                {'id': 'score', 'type': 'number', 'title': 'Score',
                 'description': '', 'required': False, 'options': []},
                {'id': 'ready', 'type': 'boolean', 'title': 'Ready',
                 'description': '', 'required': False, 'options': []},
            ],
        }
        form = FormTemplate(
            title='Statistics form', description='', definition=schema, version=2,
            settled_at=taipei_now(), created_by_id=admin.id,
        )
        db.session.add(form)
        db.session.flush()
        db.session.add_all([
            FormSubmission(
                form_id=form.id, user_id=member.id, form_version=2,
                form_snapshot={'title': form.title, 'description': '', 'schema': deepcopy(schema)},
                answers={'track': 'web', 'score': 8, 'ready': True},
            ),
            FormSubmission(
                form_id=form.id, user_id=admin.id, form_version=2,
                form_snapshot={'title': form.title, 'description': '', 'schema': deepcopy(schema)},
                answers={'track': 'game', 'score': 4, 'ready': False},
            ),
            FormSubmission(
                form_id=form.id, user_id=superadmin.id, form_version=1,
                form_snapshot={'title': form.title, 'description': '', 'schema': deepcopy(schema)},
                answers={'track': 'web', 'score': 100, 'ready': True},
            ),
        ])
        db.session.commit()
        result = {
            'form_id': form.id,
            'user_ids': [superadmin.id, admin.id, member.id],
            'superadmin_token': create_access_token(identity=str(superadmin.id)),
            'admin_token': create_access_token(identity=str(admin.id)),
        }

    yield result

    with app.app_context():
        FormTemplate.query.filter_by(id=result['form_id']).delete()
        User.query.filter(User.id.in_(result['user_ids'])).delete(synchronize_session=False)
        db.session.commit()


def bearer(token):
    return {'Authorization': f'Bearer {token}'}


def test_form_statistics_requires_superadmin(client, statistics_data):
    assert client.get('/api/superadmin/form-statistics').status_code == 401
    response = client.get(
        '/api/superadmin/form-statistics',
        headers=bearer(statistics_data['admin_token']),
    )
    assert response.status_code == 403


def test_form_statistics_aggregates_current_version_and_marks_final(client, statistics_data):
    response = client.get(
        '/api/superadmin/form-statistics',
        headers=bearer(statistics_data['superadmin_token']),
    )
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'no-store'
    payload = response.get_json()
    form = next(item for item in payload['forms'] if item['id'] == statistics_data['form_id'])
    assert form['settled'] is True
    assert form['finalizedAt']
    assert form['submissionCount'] == 2
    assert form['historicalSubmissionCount'] == 1
    assert form['questions'][0]['options'][0]['count'] == 1
    assert form['questions'][0]['options'][0]['percentage'] == 50.0
    assert form['questions'][1]['numberSummary'] == {
        'minimum': 4.0, 'maximum': 8.0, 'average': 6.0,
    }
    assert form['questions'][2]['options'][0]['count'] == 1
    assert payload['summary']['uniqueRespondents'] >= 3
