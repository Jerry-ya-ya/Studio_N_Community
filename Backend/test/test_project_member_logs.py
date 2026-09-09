import json
from pathlib import Path
from uuid import uuid4

from flask_jwt_extended import create_access_token

from models import ProjectRecruitment, Todo, User, db
from routes.admin import logs as log_routes
from routes.admin.logs import parse_project_log_line
from routes.project_recruitment import project_recruitment as project_routes


def auth_headers(token, ip):
    return {
        'Authorization': f'Bearer {token}',
        'X-Forwarded-For': f'{ip}, 10.0.0.1',
    }


def test_project_member_actions_are_logged_and_exposed_to_admin(app, client, monkeypatch):
    captured_logs = []
    monkeypatch.setattr(project_routes.project_logger, 'info', captured_logs.append)

    unique_id = uuid4().hex
    with app.app_context():
        leader = User(
            username=f'project-leader-{unique_id}',
            nickname='Project Leader',
            email=f'project-leader-{unique_id}@example.com',
            password='test-password',
            email_verified=True,
        )
        member = User(
            username=f'project-member-{unique_id}',
            nickname='Project Member',
            email=f'project-member-{unique_id}@example.com',
            password='test-password',
            email_verified=True,
        )
        admin = User(
            username=f'project-admin-{unique_id}',
            nickname='Project Admin',
            email=f'project-admin-{unique_id}@example.com',
            password='test-password',
            email_verified=True,
            role='admin',
        )
        db.session.add_all([leader, member, admin])
        db.session.flush()

        project = ProjectRecruitment(
            title='Logged project',
            summary='Project member audit log test.',
            creator_id=leader.id,
        )
        db.session.add(project)
        db.session.flush()
        todo = Todo(
            text='Completed project task',
            done=True,
            settled=False,
            project_id=project.id,
            created_by_id=leader.id,
            claimed_by_id=member.id,
        )
        db.session.add(todo)
        db.session.commit()

        project_id = project.id
        todo_id = todo.id
        user_ids = [leader.id, member.id, admin.id]
        leader_token = create_access_token(identity=str(leader.id))
        member_token = create_access_token(identity=str(member.id))
        admin_token = create_access_token(identity=str(admin.id))

    join_response = client.post(
        f'/api/project-recruitments/{project_id}/join',
        json={'message': 'I can help'},
        headers=auth_headers(member_token, '203.0.113.11'),
    )
    assert join_response.status_code == 200

    submit_response = client.post(
        f'/api/project-recruitments/{project_id}/submit-review',
        headers=auth_headers(leader_token, '203.0.113.12'),
    )
    assert submit_response.status_code == 200

    reject_response = client.post(
        f'/api/admin/project-recruitments/{project_id}/review',
        json={'action': 'reject'},
        headers=auth_headers(admin_token, '203.0.113.13'),
    )
    assert reject_response.status_code == 200

    leave_response = client.delete(
        f'/api/project-recruitments/{project_id}/join',
        headers=auth_headers(member_token, '203.0.113.14'),
    )
    assert leave_response.status_code == 200

    delete_response = client.delete(
        f'/api/project-recruitments/{project_id}',
        headers=auth_headers(leader_token, '203.0.113.15'),
    )
    assert delete_response.status_code == 200

    payloads = [json.loads(line) for line in captured_logs]
    assert [payload['action'] for payload in payloads] == [
        'join_project_recruitment',
        'submit_project_review',
        'reject_project_review',
        'leave_project_recruitment',
        'delete_project_recruitment',
    ]
    assert all(payload['event'] == 'project_member' for payload in payloads)
    assert all(payload['project_id'] == project_id for payload in payloads)
    assert [payload['ip'] for payload in payloads] == [
        '203.0.113.11',
        '203.0.113.12',
        '203.0.113.13',
        '203.0.113.14',
        '203.0.113.15',
    ]

    observed = {}

    def read_project_member_log(filename, limit):
        observed['filename'] = filename
        return Path('/logs') / filename, captured_logs[-limit:]

    monkeypatch.setattr(log_routes, 'read_backend_log', read_project_member_log)
    logs_response = client.get(
        '/api/admin/logs/project?limit=5',
        headers=auth_headers(admin_token, '203.0.113.13'),
    )
    assert logs_response.status_code == 200
    assert observed['filename'] == 'project_member.log'
    assert [item['action'] for item in logs_response.get_json()['items']] == [
        'deleted project recruitment',
        'left project recruitment',
        'rejected project settlement review',
        'submitted project settlement review',
        'joined project recruitment',
    ]

    with app.app_context():
        db.session.delete(db.session.get(Todo, todo_id))
        for user_id in user_ids:
            db.session.delete(db.session.get(User, user_id))
        db.session.commit()


def test_project_member_log_parser_keeps_legacy_creation_format():
    payload = {
        'status': 'success',
        'reason': 'created',
        'logged_at': '2026-09-09T10:00:00+08:00',
        'project_id': 33,
        'username': 'bean-leader',
        'title': 'Beanstalk launch',
        'role_needed': 'Designer',
        'max_members': 4,
        'ip': '203.0.113.20',
    }

    result = parse_project_log_line(json.dumps(payload))

    assert result['action'] == 'created project recruitment'
    assert result['target'] == '#33 Beanstalk launch / role Designer / max 4 / IP 203.0.113.20'
    assert result['rawJson'] == payload
