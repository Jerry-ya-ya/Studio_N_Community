import json
from uuid import uuid4

from flask_jwt_extended import create_access_token

from models import ProjectRecruitment, ProjectRecruitmentMember, User, db
from routes.admin.logs import parse_todo_action_log_line
from routes.todo import todo as todo_routes


class CapturingLogger:
    def __init__(self):
        self.messages = []

    def info(self, message):
        self.messages.append(message)


def auth_headers(token):
    return {'Authorization': f'Bearer {token}'}


def test_todo_lifecycle_writes_action_and_project_token_logs(client, app, monkeypatch):
    logger = CapturingLogger()
    monkeypatch.setattr(todo_routes, 'todo_action_logger', logger)

    with app.app_context():
        suffix = uuid4().hex
        leader = User(
            username=f'action-leader-{suffix}',
            nickname='Action Leader',
            email=f'action-leader-{suffix}@example.com',
            password='test-password',
            email_verified=True,
        )
        member = User(
            username=f'action-member-{suffix}',
            nickname='Action Member',
            email=f'action-member-{suffix}@example.com',
            password='test-password',
            email_verified=True,
        )
        db.session.add_all([leader, member])
        db.session.flush()
        project = ProjectRecruitment(
            title='Action log project',
            summary='Todo audit test project',
            creator_id=leader.id,
            token_budget=10,
            token_used=0,
        )
        db.session.add(project)
        db.session.flush()
        db.session.add(ProjectRecruitmentMember(project_id=project.id, user_id=member.id))
        db.session.commit()
        leader_id = leader.id
        member_id = member.id
        project_id = project.id
        leader_token = create_access_token(identity=str(leader_id))
        member_token = create_access_token(identity=str(member_id))

    create_response = client.post(
        '/api/todos',
        json={
            'text': 'Audited task',
            'project_id': project_id,
            'assign_to_team': True,
            'priority': 2,
        },
        headers=auth_headers(leader_token),
    )
    assert create_response.status_code == 201
    todo_id = create_response.get_json()['todos'][0]['id']

    assert client.put(
        f'/api/todos/{todo_id}',
        json={'claimed': True},
        headers=auth_headers(member_token),
    ).status_code == 200
    assert client.put(
        f'/api/todos/{todo_id}',
        json={'duration': 8},
        headers=auth_headers(member_token),
    ).status_code == 200
    assert client.put(
        f'/api/todos/{todo_id}',
        json={'done': True},
        headers=auth_headers(member_token),
    ).status_code == 200
    assert client.put(
        f'/api/todos/{todo_id}',
        json={'claimed': False},
        headers=auth_headers(member_token),
    ).status_code == 200
    assert client.delete(
        f'/api/todos/{todo_id}',
        headers=auth_headers(leader_token),
    ).status_code == 200

    payloads = [json.loads(message) for message in logger.messages]
    assert [payload['action'] for payload in payloads] == [
        'create',
        'deduct_project_token',
        'claim',
        'fill_time',
        'complete',
        'unclaim',
        'delete',
    ]
    assert all(payload['event'] == 'todo_action' for payload in payloads)
    assert all(payload['status'] == 'success' for payload in payloads)
    assert payloads[1]['token_cost'] == 3
    assert payloads[1]['token_used_before'] == 0
    assert payloads[1]['token_used_after'] == 3
    assert payloads[2]['actor_id'] == member_id
    assert payloads[3]['duration_before'] == 5
    assert payloads[3]['duration_after'] == 8
    assert payloads[-1]['todo_id'] == todo_id


def test_parse_todo_action_log_exposes_readable_superadmin_row():
    payload = {
        'logged_at': '2026-09-09T12:00:00+08:00',
        'status': 'success',
        'action': 'deduct_project_token',
        'actor_nickname': 'Leader',
        'todo_id': 42,
        'todo_text': 'Ship feature',
        'project_title': 'Beanstalk',
        'token_cost': 3,
        'token_used_before': 4,
        'token_used_after': 7,
        'ip': '127.0.0.1',
    }

    result = parse_todo_action_log_line(json.dumps(payload))

    assert result['actor'] == 'Leader'
    assert result['action'] == 'deducted project tokens'
    assert result['target'] == '#42 Ship feature / Beanstalk / -3 tokens / used 4 -> 7'
    assert result['status'] == 'success'
    assert result['rawJson'] == payload
