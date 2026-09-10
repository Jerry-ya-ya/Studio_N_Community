from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token

from models import ProjectRecruitment, ProjectRecruitmentMember, Todo, User, db


def auth_headers(token):
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture()
def todo_accounts(app):
    with app.app_context():
        unique_id = uuid4().hex
        leader = User(
            username=f'todo-test-leader-{unique_id}',
            nickname='Todo Leader',
            email=f'todo-test-leader-{unique_id}@example.com',
            password='test-password',
            email_verified=True,
        )
        member = User(
            username=f'todo-test-member-{unique_id}',
            nickname='Todo Member',
            email=f'todo-test-member-{unique_id}@example.com',
            password='test-password',
            email_verified=True,
        )
        outsider = User(
            username=f'todo-test-outsider-{unique_id}',
            email=f'todo-test-outsider-{unique_id}@example.com',
            password='test-password',
            email_verified=True,
        )
        db.session.add_all([leader, member, outsider])
        db.session.flush()

        project = ProjectRecruitment(
            title='Todo test project',
            summary='Project used by the Todo API pytest suite.',
            creator_id=leader.id,
            token_budget=5,
            token_used=0,
        )
        db.session.add(project)
        db.session.flush()
        db.session.add(ProjectRecruitmentMember(
            project_id=project.id,
            user_id=member.id,
        ))
        db.session.commit()

        return {
            'leader_id': leader.id,
            'member_id': member.id,
            'outsider_id': outsider.id,
            'project_id': project.id,
            'leader_token': create_access_token(identity=str(leader.id)),
            'member_token': create_access_token(identity=str(member.id)),
            'outsider_token': create_access_token(identity=str(outsider.id)),
        }


@pytest.mark.parametrize(
    ('method', 'path'),
    [
        ('get', '/api/todos'),
        ('post', '/api/todos'),
        ('put', '/api/todos/1'),
        ('delete', '/api/todos/1'),
    ],
)
def test_todo_endpoints_require_authentication(client, method, path):
    response = getattr(client, method)(path, json={} if method in {'post', 'put'} else None)

    assert response.status_code == 401


def test_personal_todo_crud_is_scoped_to_its_owner(client, app, todo_accounts):
    leader_headers = auth_headers(todo_accounts['leader_token'])
    outsider_headers = auth_headers(todo_accounts['outsider_token'])

    create_response = client.post(
        '/api/todos',
        json={'text': '  Write Todo tests  '},
        headers=leader_headers,
    )

    assert create_response.status_code == 200
    created = create_response.get_json()
    assert created['text'] == 'Write Todo tests'
    assert created['done'] is False
    assert created['settled'] is False
    assert created['priority'] == 0
    assert created['difficulty'] == 5
    assert created['duration'] == 5
    assert created['user_id'] == todo_accounts['leader_id']
    assert created['created_by_id'] == todo_accounts['leader_id']
    assert created['assignee_name'] == 'Todo Leader'
    assert created['created_by_name'] == 'Todo Leader'

    leader_list = client.get('/api/todos', headers=leader_headers)
    outsider_list = client.get('/api/todos', headers=outsider_headers)
    assert leader_list.status_code == 200
    assert created['id'] in [todo['id'] for todo in leader_list.get_json()]
    assert created['id'] not in [todo['id'] for todo in outsider_list.get_json()]

    forbidden_update = client.put(
        f"/api/todos/{created['id']}",
        json={'text': 'Changed by an outsider'},
        headers=outsider_headers,
    )
    assert forbidden_update.status_code == 404
    assert forbidden_update.get_json() == {'error': 'Not found'}

    update_response = client.put(
        f"/api/todos/{created['id']}",
        json={
            'text': 'Finish Todo coverage',
            'priority': 4,
            'difficulty': 8,
            'duration': 3,
            'claimed': True,
        },
        headers=leader_headers,
    )
    assert update_response.status_code == 200
    updated = update_response.get_json()
    assert updated['text'] == 'Finish Todo coverage'
    assert updated['priority'] == 4
    assert updated['difficulty'] == 8
    assert updated['duration'] == 3
    assert updated['claimed_by_id'] == todo_accounts['leader_id']

    done_response = client.put(
        f"/api/todos/{created['id']}",
        json={'done': True},
        headers=leader_headers,
    )
    assert done_response.status_code == 200
    assert done_response.get_json()['done'] is True

    forbidden_delete = client.delete(
        f"/api/todos/{created['id']}",
        headers=outsider_headers,
    )
    assert forbidden_delete.status_code == 404

    delete_response = client.delete(
        f"/api/todos/{created['id']}",
        headers=leader_headers,
    )
    assert delete_response.status_code == 200
    assert delete_response.get_json() == {'message': 'Deleted'}

    with app.app_context():
        assert db.session.get(Todo, created['id']) is None


@pytest.mark.parametrize(
    ('payload', 'error'),
    [
        ({}, 'Todo text is required'),
        ({'text': '   '}, 'Todo text is required'),
        ({'text': 'Invalid priority', 'priority': 5}, 'Todo priority must be between 0 and 4'),
        ({'text': 'Invalid priority', 'priority': 'high'}, 'Todo priority must be between 0 and 4'),
        ({'text': 'Invalid difficulty', 'difficulty': -1}, 'Todo difficulty must be between 0 and 9'),
        ({'text': 'Invalid duration', 'duration': 10}, 'Todo duration must be between 0 and 9'),
    ],
)
def test_create_todo_rejects_invalid_fields(client, todo_accounts, payload, error):
    response = client.post(
        '/api/todos',
        json=payload,
        headers=auth_headers(todo_accounts['leader_token']),
    )

    assert response.status_code == 400
    assert response.get_json() == {'error': error}


def test_update_todo_rejects_invalid_fields_and_completion_without_claim(
    client,
    app,
    todo_accounts,
):
    with app.app_context():
        todo = Todo(
            text='Protected Todo',
            user_id=todo_accounts['leader_id'],
            created_by_id=todo_accounts['leader_id'],
        )
        db.session.add(todo)
        db.session.commit()
        todo_id = todo.id

    headers = auth_headers(todo_accounts['leader_token'])
    invalid_cases = [
        ({'text': '  '}, 'Todo text cannot be empty'),
        ({'priority': -1}, 'Todo priority must be between 0 and 4'),
        ({'difficulty': 'hard'}, 'Todo difficulty must be between 0 and 9'),
        ({'duration': 12}, 'Todo duration must be between 0 and 9'),
    ]
    for payload, error in invalid_cases:
        response = client.put(f'/api/todos/{todo_id}', json=payload, headers=headers)
        assert response.status_code == 400
        assert response.get_json() == {'error': error}

    completion_response = client.put(
        f'/api/todos/{todo_id}',
        json={'done': True},
        headers=headers,
    )
    assert completion_response.status_code == 403
    assert completion_response.get_json() == {'error': '只能完成自己佔領的任務'}


def test_team_todo_creation_listing_claim_and_token_budget(client, app, todo_accounts):
    project_id = todo_accounts['project_id']
    leader_headers = auth_headers(todo_accounts['leader_token'])
    member_headers = auth_headers(todo_accounts['member_token'])
    outsider_headers = auth_headers(todo_accounts['outsider_token'])
    payload = {
        'text': 'Shared team task',
        'project_id': project_id,
        'assign_to_team': True,
        'priority': 2,
        'difficulty': 7,
        'duration': 4,
    }

    non_leader_response = client.post('/api/todos', json=payload, headers=member_headers)
    assert non_leader_response.status_code == 403

    invalid_assignee_response = client.post(
        '/api/todos',
        json={
            'text': 'Invalid assignee',
            'project_id': project_id,
            'assignee_user_id': todo_accounts['outsider_id'],
        },
        headers=leader_headers,
    )
    assert invalid_assignee_response.status_code == 400

    create_response = client.post('/api/todos', json=payload, headers=leader_headers)
    assert create_response.status_code == 201
    created_payload = create_response.get_json()
    assert created_payload['token_cost'] == 3
    assert created_payload['tokenCost'] == 3
    assert created_payload['project']['token_used'] == 3
    assert created_payload['project']['token_remaining'] == 2
    assert len(created_payload['todos']) == 1

    todo = created_payload['todos'][0]
    assert todo['user_id'] is None
    assert todo['project_id'] == project_id
    assert todo['project_title'] == 'Todo test project'

    member_todos = client.get(
        f'/api/todos?project_id={project_id}',
        headers=member_headers,
    )
    outsider_todos = client.get(
        f'/api/todos?project_id={project_id}',
        headers=outsider_headers,
    )
    leader_created_todos = client.get(
        f'/api/todos?project_id={project_id}&created_by_me=true',
        headers=leader_headers,
    )
    assert todo['id'] in [item['id'] for item in member_todos.get_json()]
    assert todo['id'] not in [item['id'] for item in outsider_todos.get_json()]
    assert todo['id'] in [item['id'] for item in leader_created_todos.get_json()]

    outsider_claim = client.put(
        f"/api/todos/{todo['id']}",
        json={'claimed': True},
        headers=outsider_headers,
    )
    assert outsider_claim.status_code == 404

    claim_response = client.put(
        f"/api/todos/{todo['id']}",
        json={'claimed': True},
        headers=member_headers,
    )
    assert claim_response.status_code == 200
    assert claim_response.get_json()['claimed_by_id'] == todo_accounts['member_id']

    competing_claim = client.put(
        f"/api/todos/{todo['id']}",
        json={'claimed': True},
        headers=leader_headers,
    )
    assert competing_claim.status_code == 409

    completion_response = client.put(
        f"/api/todos/{todo['id']}",
        json={'done': True},
        headers=member_headers,
    )
    assert completion_response.status_code == 200
    assert completion_response.get_json()['done'] is True

    over_budget_response = client.post(
        '/api/todos',
        json={
            'text': 'Too expensive task',
            'project_id': project_id,
            'assign_to_team': True,
            'priority': 4,
        },
        headers=leader_headers,
    )
    assert over_budget_response.status_code == 409
    assert over_budget_response.get_json() == {
        'error': '專案剩餘 Token 不足，無法發布這個 Todo'
    }

    with app.app_context():
        project = db.session.get(ProjectRecruitment, project_id)
        assert project.token_used == 3


def test_project_todo_can_be_assigned_to_a_team_member(client, todo_accounts):
    response = client.post(
        '/api/todos',
        json={
            'text': 'Member-specific task',
            'project_id': todo_accounts['project_id'],
            'assignee_user_id': todo_accounts['member_id'],
            'priority': 0,
        },
        headers=auth_headers(todo_accounts['leader_token']),
    )

    assert response.status_code == 201
    todo = response.get_json()['todos'][0]
    assert todo['user_id'] == todo_accounts['member_id']
    assert todo['assignee_name'] == 'Todo Member'


def test_project_token_consumption_triggers_level_upgrade(client, app, todo_accounts):
    with app.app_context():
        project = db.session.get(ProjectRecruitment, todo_accounts['project_id'])
        project.token_budget = 200
        project.token_used = 99
        project.level = 1
        db.session.commit()

    response = client.post(
        '/api/todos',
        json={
            'text': 'Level-up task',
            'project_id': todo_accounts['project_id'],
            'assign_to_team': True,
            'priority': 0,
        },
        headers=auth_headers(todo_accounts['leader_token']),
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload['project']['token_used'] == 100
    assert payload['project']['token_remaining'] == 100
    assert payload['project']['level'] == 2
    assert payload['level_upgraded'] is True

    with app.app_context():
        project = db.session.get(ProjectRecruitment, todo_accounts['project_id'])
        assert project.level == 2
