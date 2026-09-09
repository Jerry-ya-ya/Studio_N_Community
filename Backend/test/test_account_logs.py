from io import BytesIO
import json
from pathlib import Path
from uuid import uuid4

from flask_jwt_extended import create_access_token

from models import User, db
from routes.admin import logs as log_routes
from routes.admin.logs import parse_account_log_line
from routes.auth import account_log, avatar as avatar_routes, me as me_routes


def test_account_mutations_are_logged(app, client, monkeypatch):
    captured_logs = []
    monkeypatch.setattr(account_log.account_logger, 'info', captured_logs.append)
    monkeypatch.setattr(me_routes.mail, 'send', lambda message: None)
    monkeypatch.setattr(
        avatar_routes,
        'save_validated_image',
        lambda uploaded_file, upload_folder, prefix: f'{prefix}_avatar.png',
    )

    unique_id = uuid4().hex
    username = f'account-user-{unique_id}'
    with app.app_context():
        user = User(
            username=username,
            password='hashed-password',
            email=f'{unique_id}@example.com',
            nickname='Old nickname',
            github_url='https://github.com/old-profile',
            avatar_source='github',
            email_verified=True,
            role='user',
        )
        admin = User(
            username=f'account-admin-{unique_id}',
            password='hashed-password',
            email=f'admin-{unique_id}@example.com',
            role='admin',
        )
        db.session.add_all([user, admin])
        db.session.commit()
        user_id = user.id
        admin_id = admin.id
        user_token = create_access_token(identity=str(user.id))
        admin_token = create_access_token(identity=str(admin.id))

    headers = {
        'Authorization': f'Bearer {user_token}',
        'X-Forwarded-For': '203.0.113.30, 10.0.0.1',
    }
    update_response = client.put(
        '/api/me',
        headers=headers,
        json={
            'email': f'new-{unique_id}@example.com',
            'nickname': 'New nickname',
            'githubUrl': 'https://github.com/new-profile',
            'avatarSource': 'local',
        },
    )
    assert update_response.status_code == 200

    upload_response = client.post(
        '/api/avatar',
        headers=headers,
        data={'file': (BytesIO(b'image-data'), 'avatar.png')},
        content_type='multipart/form-data',
    )
    assert upload_response.status_code == 200

    delete_response = client.delete(
        '/api/me',
        headers=headers,
        json={'confirmation': 'DELETE'},
    )
    assert delete_response.status_code == 200

    payloads = [json.loads(line) for line in captured_logs]
    assert [payload['action'] for payload in payloads] == [
        'update_profile',
        'upload_avatar',
        'soft_delete_account',
    ]
    assert all(payload['event'] == 'account' for payload in payloads)
    assert all(payload['status'] == 'success' for payload in payloads)
    assert all(payload['user_id'] == user_id for payload in payloads)
    assert all(payload['ip'] == '203.0.113.30' for payload in payloads)
    assert set(payloads[0]['changes']) == {
        'email',
        'nickname',
        'github_url',
        'avatar_source',
    }
    assert payloads[0]['changes']['nickname'] == {
        'from': 'Old nickname',
        'to': 'New nickname',
    }
    assert payloads[1]['filename'].endswith('_avatar.png')
    assert payloads[1]['avatar_source'] == 'local'
    assert payloads[2]['username'] == username
    assert payloads[2]['previous_identity']['email'] == f'new-{unique_id}@example.com'
    assert payloads[2]['deleted_at']

    monkeypatch.setattr(
        log_routes,
        'read_backend_log',
        lambda filename, limit: (Path('/logs') / filename, captured_logs[-limit:]),
    )
    admin_headers = {'Authorization': f'Bearer {admin_token}'}
    logs_response = client.get('/api/admin/logs/account?limit=2', headers=admin_headers)
    assert logs_response.status_code == 200
    logs_body = logs_response.get_json()
    assert logs_body['type'] == 'account'
    assert logs_body['count'] == 2
    assert [item['action'] for item in logs_body['items']] == [
        'soft-deleted account',
        'uploaded avatar',
    ]

    with app.app_context():
        db.session.delete(db.session.get(User, admin_id))
        db.session.delete(db.session.get(User, user_id))
        db.session.commit()


def test_rejected_or_unchanged_profile_updates_are_not_logged(app, client, monkeypatch):
    captured_logs = []
    monkeypatch.setattr(account_log.account_logger, 'info', captured_logs.append)

    unique_id = uuid4().hex
    with app.app_context():
        user = User(
            username=f'unchanged-user-{unique_id}',
            password='hashed-password',
            email=f'{unique_id}@example.com',
            nickname='Same nickname',
            avatar_source='github',
            role='user',
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        token = create_access_token(identity=str(user.id))

    headers = {'Authorization': f'Bearer {token}'}
    unchanged_response = client.put(
        '/api/me',
        headers=headers,
        json={'nickname': 'Same nickname', 'avatarSource': 'github'},
    )
    invalid_response = client.put(
        '/api/me',
        headers=headers,
        json={'avatarSource': 'remote'},
    )

    assert unchanged_response.status_code == 200
    assert invalid_response.status_code == 400
    assert captured_logs == []

    with app.app_context():
        db.session.delete(db.session.get(User, user_id))
        db.session.commit()


def test_account_log_parser_formats_profile_change():
    payload = {
        'action': 'update_profile',
        'status': 'success',
        'logged_at': '2026-09-09T12:00:00+08:00',
        'user_id': 9,
        'username': 'bean-user',
        'role': 'user',
        'ip': '203.0.113.40',
        'changes': {
            'nickname': {'from': 'Bean', 'to': 'Jack'},
            'github_url': {'from': None, 'to': 'https://github.com/jack'},
        },
    }

    result = parse_account_log_line(json.dumps(payload))

    assert result['actor'] == 'bean-user'
    assert result['action'] == 'updated profile'
    assert result['target'] == '#9 fields nickname, github_url / role user / IP 203.0.113.40'
    assert result['status'] == 'success'
    assert result['rawJson'] == payload
