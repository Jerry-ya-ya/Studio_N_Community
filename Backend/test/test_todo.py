from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token

from models import ProjectRecruitment, ProjectRecruitmentMember, Todo, TodoRequest, User, db


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
        ('get', '/api/todo-requests'),
        ('post', '/api/project-recruitments/1/todo-requests'),
        ('post', '/api/todo-requests/1/decision'),
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


def test_leader_self_completion_setting_is_owner_controlled_and_enforced(
    client,
    todo_accounts,
):
    project_id = todo_accounts['project_id']
    leader_headers = auth_headers(todo_accounts['leader_token'])
    member_headers = auth_headers(todo_accounts['member_token'])

    captain_todo_response = client.post(
        '/api/todos',
        json={
            'text': 'Existing captain task',
            'project_id': project_id,
            'assignee_user_id': todo_accounts['leader_id'],
        },
        headers=leader_headers,
    )
    assert captain_todo_response.status_code == 201
    captain_todo = captain_todo_response.get_json()['todos'][0]
    claim_response = client.put(
        f"/api/todos/{captain_todo['id']}",
        json={'claimed': True},
        headers=leader_headers,
    )
    assert claim_response.status_code == 200

    member_update = client.put(
        f'/api/project-recruitments/{project_id}/todo-settings',
        json={'leader_self_completion_blocked': True},
        headers=member_headers,
    )
    assert member_update.status_code == 403

    invalid_update = client.put(
        f'/api/project-recruitments/{project_id}/todo-settings',
        json={'leader_self_completion_blocked': 'yes'},
        headers=leader_headers,
    )
    assert invalid_update.status_code == 400

    enable_response = client.put(
        f'/api/project-recruitments/{project_id}/todo-settings',
        json={'leader_self_completion_blocked': True},
        headers=leader_headers,
    )
    assert enable_response.status_code == 200
    assert enable_response.get_json()['leader_self_completion_blocked'] is True

    forbidden_completion = client.put(
        f"/api/todos/{captain_todo['id']}",
        json={'done': True},
        headers=leader_headers,
    )
    assert forbidden_completion.status_code == 403
    assert forbidden_completion.get_json() == {
        'error': '組長不能完成自己建立的任務'
    }

    forbidden_assignment = client.post(
        '/api/todos',
        json={
            'text': 'New captain task',
            'project_id': project_id,
            'assignee_user_id': todo_accounts['leader_id'],
        },
        headers=leader_headers,
    )
    assert forbidden_assignment.status_code == 409
    assert forbidden_assignment.get_json() == {
        'error': '已禁止組長建立由自己完成的任務'
    }

    team_todo_response = client.post(
        '/api/todos',
        json={
            'text': 'Team-owned task',
            'project_id': project_id,
            'assign_to_team': True,
        },
        headers=leader_headers,
    )
    assert team_todo_response.status_code == 201
    team_todo = team_todo_response.get_json()['todos'][0]

    forbidden_claim = client.put(
        f"/api/todos/{team_todo['id']}",
        json={'claimed': True},
        headers=leader_headers,
    )
    assert forbidden_claim.status_code == 403
    assert forbidden_claim.get_json() == {
        'error': '組長不能佔領自己建立的任務'
    }

    member_claim = client.put(
        f"/api/todos/{team_todo['id']}",
        json={'claimed': True},
        headers=member_headers,
    )
    assert member_claim.status_code == 200
    member_completion = client.put(
        f"/api/todos/{team_todo['id']}",
        json={'done': True},
        headers=member_headers,
    )
    assert member_completion.status_code == 200
    assert member_completion.get_json()['done'] is True


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


def test_member_todo_request_acceptance_creates_claimed_task(client, app, todo_accounts):
    project_id = todo_accounts['project_id']
    member_headers = auth_headers(todo_accounts['member_token'])
    leader_headers = auth_headers(todo_accounts['leader_token'])

    create_response = client.post(
        f'/api/project-recruitments/{project_id}/todo-requests',
        json={'text': '  Add keyboard navigation  '},
        headers=member_headers,
    )
    assert create_response.status_code == 201
    request_payload = create_response.get_json()
    assert request_payload['text'] == 'Add keyboard navigation'
    assert request_payload['status'] == 'pending'
    assert request_payload['requested_by_id'] == todo_accounts['member_id']

    leader_list = client.get('/api/todo-requests', headers=leader_headers)
    member_list = client.get('/api/todo-requests', headers=member_headers)
    outsider_list = client.get('/api/todo-requests', headers=auth_headers(todo_accounts['outsider_token']))
    assert request_payload['id'] in [item['id'] for item in leader_list.get_json()]
    assert request_payload['id'] in [item['id'] for item in member_list.get_json()]
    assert request_payload['id'] not in [item['id'] for item in outsider_list.get_json()]

    accept_response = client.post(
        f"/api/todo-requests/{request_payload['id']}/decision",
        json={'decision': 'accepted', 'priority': 2},
        headers=leader_headers,
    )
    assert accept_response.status_code == 200
    accepted = accept_response.get_json()
    assert accepted['request']['status'] == 'accepted'
    assert accepted['request']['priority'] == 2
    assert accepted['token_cost'] == 3
    assert accepted['project']['token_used'] == 3
    assert accepted['todo']['user_id'] == todo_accounts['member_id']
    assert accepted['todo']['claimed_by_id'] == todo_accounts['member_id']

    member_todos = client.get('/api/todos', headers=member_headers).get_json()
    assert accepted['todo']['id'] in [todo['id'] for todo in member_todos]

    with app.app_context():
        stored_request = db.session.get(TodoRequest, request_payload['id'])
        assert stored_request.accepted_todo_id == accepted['todo']['id']


def test_todo_request_permissions_rejection_and_validation(client, todo_accounts):
    project_id = todo_accounts['project_id']
    leader_headers = auth_headers(todo_accounts['leader_token'])
    member_headers = auth_headers(todo_accounts['member_token'])
    outsider_headers = auth_headers(todo_accounts['outsider_token'])

    assert client.post(
        f'/api/project-recruitments/{project_id}/todo-requests',
        json={'text': 'Leader request'},
        headers=leader_headers,
    ).status_code == 403
    assert client.post(
        f'/api/project-recruitments/{project_id}/todo-requests',
        json={'text': 'Outsider request'},
        headers=outsider_headers,
    ).status_code == 403
    assert client.post(
        f'/api/project-recruitments/{project_id}/todo-requests',
        json={'text': '   '},
        headers=member_headers,
    ).status_code == 400

    created = client.post(
        f'/api/project-recruitments/{project_id}/todo-requests',
        json={'text': 'Document the API'},
        headers=member_headers,
    ).get_json()
    assert client.post(
        f"/api/todo-requests/{created['id']}/decision",
        json={'decision': 'accepted'},
        headers=leader_headers,
    ).status_code == 400
    assert client.post(
        f"/api/todo-requests/{created['id']}/decision",
        json={'decision': 'rejected'},
        headers=member_headers,
    ).status_code == 403

    rejected = client.post(
        f"/api/todo-requests/{created['id']}/decision",
        json={'decision': 'rejected'},
        headers=leader_headers,
    )
    assert rejected.status_code == 200
    assert rejected.get_json()['request']['status'] == 'rejected'
    assert rejected.get_json()['todo'] is None
    assert client.post(
        f"/api/todo-requests/{created['id']}/decision",
        json={'decision': 'accepted', 'priority': 0},
        headers=leader_headers,
    ).status_code == 409
