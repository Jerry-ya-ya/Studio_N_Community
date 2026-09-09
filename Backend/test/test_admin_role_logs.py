import json
from pathlib import Path
from uuid import uuid4

from flask_jwt_extended import create_access_token

from models import User, db
from routes.admin import logs as log_routes
from routes.admin import promote as promote_routes
from routes.admin.logs import parse_admin_role_log_line


def test_superadmin_role_changes_are_logged(app, client, monkeypatch):
    captured_logs = []
    monkeypatch.setattr(promote_routes.admin_role_logger, 'info', captured_logs.append)

    unique_id = uuid4().hex
    with app.app_context():
        superadmin = User(
            username=f'role-superadmin-{unique_id}',
            password='hashed-password',
            email=f'role-superadmin-{unique_id}@example.com',
            nickname='Role Keeper',
            role='superadmin',
        )
        target = User(
            username=f'role-target-{unique_id}',
            password='hashed-password',
            email=f'role-target-{unique_id}@example.com',
            nickname='Bean Climber',
            role='user',
        )
        db.session.add_all([superadmin, target])
        db.session.commit()
        superadmin_id = superadmin.id
        target_id = target.id
        target_username = target.username
        token = create_access_token(identity=str(superadmin.id))

    headers = {
        'Authorization': f'Bearer {token}',
        'X-Forwarded-For': '203.0.113.29, 10.0.0.1',
    }

    promote_response = client.put(f'/api/superadmin/promote/{target_id}', headers=headers)
    assert promote_response.status_code == 200

    demote_response = client.put(f'/api/superadmin/demote/{target_id}', headers=headers)
    assert demote_response.status_code == 200

    payloads = [json.loads(line) for line in captured_logs]
    assert [payload['action'] for payload in payloads] == ['promote_user', 'demote_user']
    assert [payload['previous_role'] for payload in payloads] == ['user', 'admin']
    assert [payload['new_role'] for payload in payloads] == ['admin', 'user']
    assert all(payload['event'] == 'admin_role' for payload in payloads)
    assert all(payload['status'] == 'success' for payload in payloads)
    assert all(payload['admin_id'] == superadmin_id for payload in payloads)
    assert all(payload['superadmin_id'] == superadmin_id for payload in payloads)
    assert all(payload['username'] == f'role-superadmin-{unique_id}' for payload in payloads)
    assert all(payload['nickname'] == 'Role Keeper' for payload in payloads)
    assert all(payload['role'] == 'superadmin' for payload in payloads)
    assert all(payload['ip'] == '203.0.113.29' for payload in payloads)
    assert all(payload['target_user_id'] == target_id for payload in payloads)
    assert all(payload['target_username'] == target_username for payload in payloads)
    assert all(payload['target_nickname'] == 'Bean Climber' for payload in payloads)
    assert all(payload['logged_at'] for payload in payloads)

    monkeypatch.setattr(
        log_routes,
        'read_backend_log',
        lambda filename, limit: (Path('/logs') / filename, captured_logs[-limit:]),
    )
    logs_response = client.get(
        '/api/superadmin/logs/admin-role?limit=2',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert logs_response.status_code == 200
    logs_body = logs_response.get_json()
    assert logs_body['type'] == 'admin-role'
    assert logs_body['count'] == 2
    assert [item['action'] for item in logs_body['items']] == [
        'demoted admin to user',
        'promoted user to admin',
    ]
    assert logs_body['items'][0]['target'] == f'#{target_id} Bean Climber / admin -> user / IP 203.0.113.29'
    assert logs_body['items'][0]['rawJson']['target_username'] == target_username

    with app.app_context():
        db.session.delete(db.session.get(User, target_id))
        db.session.delete(db.session.get(User, superadmin_id))
        db.session.commit()


def test_unchanged_roles_do_not_create_admin_role_logs(app, client, monkeypatch):
    captured_logs = []
    monkeypatch.setattr(promote_routes.admin_role_logger, 'info', captured_logs.append)

    unique_id = uuid4().hex
    with app.app_context():
        superadmin = User(
            username=f'noop-superadmin-{unique_id}',
            password='hashed-password',
            email=f'noop-superadmin-{unique_id}@example.com',
            role='superadmin',
        )
        target = User(
            username=f'noop-admin-{unique_id}',
            password='hashed-password',
            email=f'noop-admin-{unique_id}@example.com',
            role='admin',
        )
        db.session.add_all([superadmin, target])
        db.session.commit()
        superadmin_id = superadmin.id
        target_id = target.id
        token = create_access_token(identity=str(superadmin.id))

    headers = {'Authorization': f'Bearer {token}'}
    promote_response = client.put(f'/api/superadmin/promote/{target_id}', headers=headers)
    assert promote_response.status_code == 200
    assert captured_logs == []

    with app.app_context():
        db.session.delete(db.session.get(User, target_id))
        db.session.delete(db.session.get(User, superadmin_id))
        db.session.commit()


def test_admin_role_log_parser_handles_legacy_entries():
    result = parse_admin_role_log_line('old role entry')

    assert result['actor'] == 'Superadmin'
    assert result['status'] == 'notice'
    assert result['rawJson'] is None
