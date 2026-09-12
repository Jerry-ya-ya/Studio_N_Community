import json
from pathlib import Path
from uuid import uuid4

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from models import User, db
from routes.admin import logs as log_routes
from routes.admin.logs import parse_security_log_line
from routes.auth import email as email_routes
from routes.auth import security_log


OLD_PASSWORD = 'Original!Cedar47Path'
NEW_PASSWORD = 'Updated!Maple58Trail'


def test_security_mutations_are_logged_and_visible_to_superadmin(app, client, monkeypatch):
    captured_logs = []
    monkeypatch.setattr(security_log.security_logger, 'info', captured_logs.append)
    monkeypatch.setattr(email_routes.mail, 'send', lambda message: None)

    suffix = uuid4().hex
    with app.app_context():
        account_user = User(
            username=f'security-account-{suffix}',
            email=f'security-account-{suffix}@example.com',
            password=generate_password_hash(OLD_PASSWORD),
            email_verified=True,
            role='user',
        )
        verify_user = User(
            username=f'security-verify-{suffix}',
            email=f'security-verify-{suffix}@example.com',
            password=generate_password_hash(OLD_PASSWORD),
            email_verified=False,
            role='user',
        )
        resend_user = User(
            username=f'security-resend-{suffix}',
            email=f'security-resend-{suffix}@example.com',
            password=generate_password_hash(OLD_PASSWORD),
            email_verified=False,
            role='user',
        )
        superadmin = User(
            username=f'security-superadmin-{suffix}',
            email=f'security-superadmin-{suffix}@example.com',
            password=generate_password_hash(OLD_PASSWORD),
            email_verified=True,
            role='superadmin',
        )
        db.session.add_all([account_user, verify_user, resend_user, superadmin])
        db.session.commit()
        user_ids = [account_user.id, verify_user.id, resend_user.id, superadmin.id]
        account_token = create_access_token(identity=str(account_user.id))
        superadmin_token = create_access_token(identity=str(superadmin.id))
        verification_token = email_routes.generate_confirmation_token(verify_user.email)

    headers = {
        'Authorization': f'Bearer {account_token}',
        'X-Forwarded-For': '203.0.113.80, 10.0.0.1',
    }
    password_response = client.put(
        '/api/changepassword',
        headers=headers,
        json={'old_password': OLD_PASSWORD, 'new_password': NEW_PASSWORD},
    )
    assert password_response.status_code == 200

    verify_response = client.get(
        f'/api/verify-email/{verification_token}',
        environ_overrides={'REMOTE_ADDR': '203.0.113.81'},
    )
    assert verify_response.status_code == 302

    resend_response = client.post(
        '/api/resendverification',
        json={'email': f'security-resend-{suffix}@example.com'},
        environ_overrides={'REMOTE_ADDR': '203.0.113.82'},
    )
    assert resend_response.status_code == 200

    login_response = client.post(
        '/api/login',
        json={
            'username': f'security-account-{suffix}',
            'password': NEW_PASSWORD,
            'remember_me': True,
        },
        environ_overrides={'REMOTE_ADDR': '203.0.113.83'},
    )
    assert login_response.status_code == 200
    logout_response = client.delete(
        '/api/refresh',
        environ_overrides={'REMOTE_ADDR': '203.0.113.84'},
    )
    assert logout_response.status_code == 200

    payloads = [json.loads(line) for line in captured_logs]
    assert [payload['action'] for payload in payloads] == [
        'change_password',
        'verify_email',
        'resend_verification_email',
        'clear_refresh_token',
    ]
    assert all(payload['event'] == 'security' for payload in payloads)
    assert all(payload['status'] == 'success' for payload in payloads)
    assert payloads[0]['ip'] == '203.0.113.80'
    assert payloads[-1]['had_refresh_cookie'] is True
    assert payloads[-1]['username'] == f'security-account-{suffix}'

    monkeypatch.setattr(
        log_routes,
        'read_backend_log',
        lambda filename, limit: (Path('/logs') / filename, captured_logs[-limit:]),
    )
    user_log_response = client.get(
        '/api/superadmin/logs/security',
        headers={'Authorization': f'Bearer {account_token}'},
    )
    assert user_log_response.status_code == 403

    logs_response = client.get(
        '/api/superadmin/logs/security?limit=4',
        headers={'Authorization': f'Bearer {superadmin_token}'},
    )
    assert logs_response.status_code == 200
    logs_body = logs_response.get_json()
    assert logs_body['type'] == 'security'
    assert logs_body['count'] == 4
    assert [item['action'] for item in logs_body['items']] == [
        'cleared refresh token / logged out',
        'resent verification email',
        'verified email',
        'changed password',
    ]

    with app.app_context():
        for user_id in user_ids:
            db.session.delete(db.session.get(User, user_id))
        db.session.commit()


def test_security_log_parser_handles_legacy_and_structured_entries():
    legacy = parse_security_log_line('old security entry')
    assert legacy['status'] == 'notice'
    assert legacy['rawJson'] is None

    payload = {
        'action': 'verify_email',
        'status': 'success',
        'logged_at': '2026-09-09T12:00:00+08:00',
        'user_id': 7,
        'username': 'bean-user',
        'email': 'bean@example.com',
        'role': 'user',
        'ip': '203.0.113.90',
    }
    result = parse_security_log_line(json.dumps(payload))
    assert result['actor'] == 'bean-user'
    assert result['action'] == 'verified email'
    assert result['target'] == '#7 bean@example.com / role user / IP 203.0.113.90'
    assert result['rawJson'] == payload
