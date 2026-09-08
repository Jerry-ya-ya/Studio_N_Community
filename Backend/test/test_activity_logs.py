from io import BytesIO
import json
from pathlib import Path
from uuid import uuid4

from flask_jwt_extended import create_access_token

from models import ActivityPromotion, User, db
from routes.admin import activity as activity_routes
from routes.admin import logs as log_routes
from routes.admin.logs import parse_activity_log_line


def test_admin_activity_mutations_are_logged(app, client, monkeypatch):
    captured_logs = []
    monkeypatch.setattr(activity_routes.activity_logger, 'info', captured_logs.append)
    monkeypatch.setattr(
        activity_routes,
        'save_validated_image',
        lambda uploaded_file, upload_folder, prefix: f'{prefix}_test.png',
    )

    unique_id = uuid4().hex
    username = f'activity-admin-{unique_id}'
    with app.app_context():
        admin = User(
            username=username,
            password='hashed-password',
            email=f'{unique_id}@example.com',
            role='admin',
        )
        db.session.add(admin)
        db.session.commit()
        token = create_access_token(identity=str(admin.id))

    headers = {
        'Authorization': f'Bearer {token}',
        'X-Forwarded-For': '203.0.113.10, 10.0.0.1',
    }
    create_response = client.post(
        '/api/admin/activities',
        headers=headers,
        json={
            'title': 'Launch event',
            'description': 'Initial details',
            'visibility': 'private',
            'targetFilter': 'all',
        },
    )
    assert create_response.status_code == 201
    activity_id = create_response.get_json()['id']

    update_response = client.put(
        f'/api/admin/activities/{activity_id}',
        headers=headers,
        json={
            'title': 'Updated launch event',
            'description': 'Updated details',
            'visibility': 'public',
            'targetFilter': 'role:user',
            'sort_order': 3,
        },
    )
    assert update_response.status_code == 200

    upload_response = client.post(
        f'/api/admin/activities/{activity_id}/image',
        headers=headers,
        data={'file': (BytesIO(b'image-data'), 'event.png')},
        content_type='multipart/form-data',
    )
    assert upload_response.status_code == 200

    clear_response = client.delete(
        f'/api/admin/activities/{activity_id}/image',
        headers=headers,
    )
    assert clear_response.status_code == 200

    delete_response = client.delete(
        f'/api/admin/activities/{activity_id}',
        headers=headers,
    )
    assert delete_response.status_code == 200

    payloads = [json.loads(line) for line in captured_logs]
    assert [payload['action'] for payload in payloads] == [
        'create_activity',
        'update_activity',
        'upload_activity_image',
        'clear_activity_image',
        'delete_activity',
    ]
    assert all(payload['activity_id'] == activity_id for payload in payloads)
    assert all(payload['admin_id'] for payload in payloads)
    assert all(payload['username'] == username for payload in payloads)
    assert all(payload['ip'] == '203.0.113.10' for payload in payloads)
    assert payloads[1]['changes']['title'] == {
        'from': 'Launch event',
        'to': 'Updated launch event',
    }
    assert payloads[2]['image_url'].endswith(f'activity-{activity_id}_test.png')

    monkeypatch.setattr(
        log_routes,
        'read_backend_log',
        lambda filename, limit: (Path('/logs') / filename, captured_logs[-limit:]),
    )
    logs_response = client.get('/api/admin/logs/activity?limit=3', headers=headers)
    assert logs_response.status_code == 200
    logs_body = logs_response.get_json()
    assert logs_body['type'] == 'activity'
    assert logs_body['count'] == 3
    assert [item['action'] for item in logs_body['items']] == [
        'deleted activity',
        'cleared activity image',
        'uploaded activity image',
    ]

    with app.app_context():
        assert db.session.get(ActivityPromotion, activity_id) is None
        db.session.delete(db.session.get(User, payloads[0]['admin_id']))
        db.session.commit()


def test_activity_log_parser_formats_admin_log_row():
    payload = {
        'action': 'upload_activity_image',
        'status': 'success',
        'logged_at': '2026-09-08T12:00:00+08:00',
        'admin_id': 7,
        'username': 'bean-admin',
        'role': 'admin',
        'ip': '203.0.113.20',
        'activity_id': 28,
        'title': 'Beanstalk meetup',
        'visibility': 'public',
    }

    result = parse_activity_log_line(json.dumps(payload))

    assert result['actor'] == 'bean-admin'
    assert result['action'] == 'uploaded activity image'
    assert result['target'] == '#28 Beanstalk meetup / public / role admin / IP 203.0.113.20'
    assert result['status'] == 'success'
    assert result['rawJson'] == payload
