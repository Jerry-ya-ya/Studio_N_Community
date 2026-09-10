from datetime import date
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token

from models import DailyCheckIn, ProjectRecruitment, ProjectRecruitmentMember, Todo, User, db
from routes.project_recruitment.project_recruitment import (
    TODO_REWARD_COIN_DATE,
    get_todo_reward_breakdown,
)
from routes.project_recruitment import project_recruitment as recruitment_routes


def auth_headers(token):
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture()
def recruitment_accounts(app):
    suffix = uuid4().hex
    with app.app_context():
        users = {
            'leader': User(
                username=f'project-leader-{suffix}',
                nickname='Project Leader',
                email=f'project-leader-{suffix}@example.com',
                password='test-password',
                email_verified=True,
            ),
            'member': User(
                username=f'project-member-{suffix}',
                nickname='Project Member',
                email=f'project-member-{suffix}@example.com',
                password='test-password',
                email_verified=True,
            ),
            'outsider': User(
                username=f'project-outsider-{suffix}',
                email=f'project-outsider-{suffix}@example.com',
                password='test-password',
                email_verified=True,
            ),
            'admin': User(
                username=f'project-admin-{suffix}',
                nickname='Project Admin',
                email=f'project-admin-{suffix}@example.com',
                password='test-password',
                email_verified=True,
                role='admin',
            ),
        }
        db.session.add_all(users.values())
        db.session.commit()

        result = {}
        for name, user in users.items():
            result[f'{name}_id'] = user.id
            result[f'{name}_token'] = create_access_token(identity=str(user.id))
        result['missing_token'] = create_access_token(identity='999999999')
        return result


def add_project(app, creator_id, **overrides):
    with app.app_context():
        project = ProjectRecruitment(
            title=overrides.pop('title', 'Recruitment test project'),
            summary=overrides.pop('summary', 'A project used by the recruitment API tests.'),
            creator_id=creator_id,
            **overrides,
        )
        db.session.add(project)
        db.session.commit()
        return project.id


def add_todo(app, project_id, **overrides):
    with app.app_context():
        todo = Todo(
            text=overrides.pop('text', 'Project task'),
            project_id=project_id,
            **overrides,
        )
        db.session.add(todo)
        db.session.commit()
        return todo.id


@pytest.mark.parametrize(
    ('method', 'path'),
    [
        ('get', '/api/project-recruitments'),
        ('post', '/api/project-recruitments'),
        ('post', '/api/project-recruitments/1/join'),
        ('delete', '/api/project-recruitments/1/join'),
        ('post', '/api/project-recruitments/1/submit-review'),
        ('delete', '/api/project-recruitments/1'),
        ('get', '/api/admin/project-recruitments'),
        ('put', '/api/admin/project-todos/1/difficulty'),
        ('post', '/api/admin/project-recruitments/1/review'),
    ],
)
def test_recruitment_endpoints_require_authentication(client, method, path):
    response = getattr(client, method)(path, json={} if method in {'post', 'put'} else None)
    assert response.status_code == 401


@pytest.mark.parametrize(
    ('method', 'path'),
    [
        ('get', '/api/project-recruitments'),
        ('post', '/api/project-recruitments'),
        ('post', '/api/project-recruitments/1/join'),
        ('delete', '/api/project-recruitments/1/join'),
        ('post', '/api/project-recruitments/1/submit-review'),
        ('delete', '/api/project-recruitments/1'),
    ],
)
def test_recruitment_endpoints_reject_tokens_for_missing_users(
    client,
    recruitment_accounts,
    method,
    path,
):
    response = getattr(client, method)(
        path,
        json={} if method == 'post' else None,
        headers=auth_headers(recruitment_accounts['missing_token']),
    )
    assert response.status_code == 404
    assert response.get_json() == {'error': 'User not found'}


def test_create_and_list_project_recruitments(client, recruitment_accounts):
    headers = auth_headers(recruitment_accounts['leader_token'])
    response = client.post(
        '/api/project-recruitments',
        json={
            'title': '  Coverage project  ',
            'summary': '  Recruit people and ship tests.  ',
            'role_needed': '  Backend engineer  ',
            'contact': '  team@example.com  ',
            'max_members': '2',
        },
        headers={**headers, 'X-Forwarded-For': '203.0.113.8, 10.0.0.1'},
    )

    assert response.status_code == 201
    project = response.get_json()
    assert project['title'] == 'Coverage project'
    assert project['summary'] == 'Recruit people and ship tests.'
    assert project['role_needed'] == 'Backend engineer'
    assert project['contact'] == 'team@example.com'
    assert project['max_members'] == 2
    assert project['review_status'] == 'open'
    assert project['token_budget'] == project['tokenBudget'] == 100
    assert project['token_used'] == project['tokenUsed'] == 0
    assert project['token_remaining'] == project['tokenRemaining'] == 100
    assert project['owned_by_me'] is True
    assert project['joined_by_me'] is False
    assert project['members'] == []
    assert project['todos'] == []

    listed = client.get('/api/project-recruitments', headers=headers)
    assert listed.status_code == 200
    assert project['id'] in [item['id'] for item in listed.get_json()]

    missing_user = client.get(
        '/api/project-recruitments',
        headers=auth_headers(recruitment_accounts['missing_token']),
    )
    assert missing_user.status_code == 404
    assert missing_user.get_json() == {'error': 'User not found'}


@pytest.mark.parametrize(
    ('payload', 'error'),
    [
        ({'summary': 'Summary'}, '請填寫專案名稱'),
        ({'title': 'Title'}, '請填寫招募內容'),
        ({'title': 'Title', 'summary': 'Summary', 'max_members': 'many'}, '人數上限必須是數字'),
        ({'title': 'Title', 'summary': 'Summary', 'max_members': 0}, '人數上限至少為 1'),
    ],
)
def test_create_project_recruitment_validates_required_fields(
    client,
    recruitment_accounts,
    payload,
    error,
):
    response = client.post(
        '/api/project-recruitments',
        json=payload,
        headers=auth_headers(recruitment_accounts['leader_token']),
    )
    assert response.status_code == 400
    assert response.get_json() == {'error': error}


def test_create_project_accepts_an_unlimited_member_count(client, recruitment_accounts):
    response = client.post(
        '/api/project-recruitments',
        json={'title': 'Unlimited', 'summary': 'No member cap', 'max_members': ''},
        headers=auth_headers(recruitment_accounts['leader_token']),
    )
    assert response.status_code == 201
    assert response.get_json()['max_members'] is None


def test_join_duplicate_capacity_and_leave_flows(client, app, recruitment_accounts):
    project_id = add_project(app, recruitment_accounts['leader_id'], max_members=1)
    leader_headers = auth_headers(recruitment_accounts['leader_token'])
    member_headers = auth_headers(recruitment_accounts['member_token'])
    outsider_headers = auth_headers(recruitment_accounts['outsider_token'])

    own_join = client.post(f'/api/project-recruitments/{project_id}/join', headers=leader_headers)
    assert own_join.status_code == 400

    joined = client.post(
        f'/api/project-recruitments/{project_id}/join',
        json={'message': '  I can help  '},
        headers=member_headers,
    )
    assert joined.status_code == 200
    payload = joined.get_json()
    assert payload['joined_by_me'] is True
    assert payload['member_count'] == 1
    assert payload['members'][0]['message'] == 'I can help'
    assert payload['members'][0]['user']['nickname'] == 'Project Member'
    assert payload['members'][0]['created_at']

    # Capacity is checked before the uniqueness constraint, so temporarily remove the cap
    # to exercise the idempotent duplicate-join response.
    with app.app_context():
        db.session.get(ProjectRecruitment, project_id).max_members = None
        db.session.commit()
    duplicate = client.post(f'/api/project-recruitments/{project_id}/join', headers=member_headers)
    assert duplicate.status_code == 200
    assert duplicate.get_json() == {'message': '你已經登記加入此招募'}

    with app.app_context():
        db.session.get(ProjectRecruitment, project_id).max_members = 1
        db.session.commit()
    full = client.post(f'/api/project-recruitments/{project_id}/join', headers=outsider_headers)
    assert full.status_code == 400
    assert full.get_json() == {'error': '招募名額已滿'}

    not_joined = client.delete(f'/api/project-recruitments/{project_id}/join', headers=outsider_headers)
    assert not_joined.status_code == 404

    left = client.delete(f'/api/project-recruitments/{project_id}/join', headers=member_headers)
    assert left.status_code == 200
    assert left.get_json()['joined_by_me'] is False
    assert left.get_json()['member_count'] == 0


def test_admin_listing_and_project_deletion_permissions(client, app, recruitment_accounts):
    project_id = add_project(app, recruitment_accounts['leader_id'])
    member_headers = auth_headers(recruitment_accounts['member_token'])

    forbidden_admin_list = client.get('/api/admin/project-recruitments', headers=member_headers)
    assert forbidden_admin_list.status_code == 403

    admin_list = client.get(
        '/api/admin/project-recruitments',
        headers=auth_headers(recruitment_accounts['admin_token']),
    )
    assert admin_list.status_code == 200
    assert project_id in [project['id'] for project in admin_list.get_json()]

    forbidden_delete = client.delete(f'/api/project-recruitments/{project_id}', headers=member_headers)
    assert forbidden_delete.status_code == 403

    deleted = client.delete(
        f'/api/project-recruitments/{project_id}',
        headers=auth_headers(recruitment_accounts['leader_token']),
    )
    assert deleted.status_code == 200
    assert deleted.get_json() == {'message': '招募已刪除', 'id': project_id}
    with app.app_context():
        assert db.session.get(ProjectRecruitment, project_id) is None


def test_submit_review_requires_leader_and_completed_unsettled_todo(
    client,
    app,
    recruitment_accounts,
):
    project_id = add_project(app, recruitment_accounts['leader_id'])
    leader_headers = auth_headers(recruitment_accounts['leader_token'])

    forbidden = client.post(
        f'/api/project-recruitments/{project_id}/submit-review',
        headers=auth_headers(recruitment_accounts['member_token']),
    )
    assert forbidden.status_code == 403

    empty = client.post(f'/api/project-recruitments/{project_id}/submit-review', headers=leader_headers)
    assert empty.status_code == 409

    add_todo(
        app,
        project_id,
        done=True,
        settled=False,
        claimed_by_id=recruitment_accounts['member_id'],
    )
    submitted = client.post(
        f'/api/project-recruitments/{project_id}/submit-review',
        headers=leader_headers,
    )
    assert submitted.status_code == 200
    assert submitted.get_json()['review_status'] == 'pending'

    duplicate = client.post(
        f'/api/project-recruitments/{project_id}/submit-review',
        headers=leader_headers,
    )
    assert duplicate.status_code == 409
    assert duplicate.get_json() == {'error': '此專案已在審理中'}


@pytest.mark.parametrize('difficulty', [None, 'hard', 1, 14])
def test_admin_difficulty_scoring_rejects_invalid_values(
    client,
    app,
    recruitment_accounts,
    difficulty,
):
    project_id = add_project(app, recruitment_accounts['leader_id'])
    todo_id = add_todo(app, project_id, done=True)
    response = client.put(
        f'/api/admin/project-todos/{todo_id}/difficulty',
        json={'difficulty': difficulty},
        headers=auth_headers(recruitment_accounts['admin_token']),
    )
    assert response.status_code == 400
    assert response.get_json() == {'error': 'Todo difficulty must be one of 2, 4, 6, 9, 13'}


def test_admin_scores_only_completed_unsettled_project_todos(client, app, recruitment_accounts):
    project_id = add_project(app, recruitment_accounts['leader_id'])
    todo_id = add_todo(app, project_id, done=False, priority=0, duration=2)
    admin_headers = auth_headers(recruitment_accounts['admin_token'])

    incomplete = client.put(
        f'/api/admin/project-todos/{todo_id}/difficulty',
        json={'difficulty': 9},
        headers=admin_headers,
    )
    assert incomplete.status_code == 409

    with app.app_context():
        todo = db.session.get(Todo, todo_id)
        todo.done = True
        db.session.commit()
    scored = client.put(
        f'/api/admin/project-todos/{todo_id}/difficulty',
        json={'difficulty': 9},
        headers=admin_headers,
    )
    assert scored.status_code == 200
    assert scored.get_json()['difficulty'] == 9
    assert scored.get_json()['reward_coins'] == scored.get_json()['rewardCoins'] == 18

    with app.app_context():
        todo = db.session.get(Todo, todo_id)
        todo.settled = True
        db.session.commit()
    settled = client.put(
        f'/api/admin/project-todos/{todo_id}/difficulty',
        json={'difficulty': 13},
        headers=admin_headers,
    )
    assert settled.status_code == 409


def test_admin_review_rejects_invalid_states_and_can_reject(client, app, recruitment_accounts):
    project_id = add_project(app, recruitment_accounts['leader_id'])
    admin_headers = auth_headers(recruitment_accounts['admin_token'])

    not_pending = client.post(
        f'/api/admin/project-recruitments/{project_id}/review',
        json={'action': 'approve'},
        headers=admin_headers,
    )
    assert not_pending.status_code == 409

    with app.app_context():
        project = db.session.get(ProjectRecruitment, project_id)
        project.review_status = 'pending'
        db.session.commit()
    invalid = client.post(
        f'/api/admin/project-recruitments/{project_id}/review',
        json={'action': 'maybe'},
        headers=admin_headers,
    )
    assert invalid.status_code == 400

    rejected = client.post(
        f'/api/admin/project-recruitments/{project_id}/review',
        json={'action': 'reject'},
        headers=admin_headers,
    )
    assert rejected.status_code == 200
    assert rejected.get_json()['review_status'] == 'rejected'


def test_admin_approve_requires_a_pending_todo(client, app, recruitment_accounts):
    project_id = add_project(app, recruitment_accounts['leader_id'], review_status='pending')
    response = client.post(
        f'/api/admin/project-recruitments/{project_id}/review',
        json={'action': 'approve'},
        headers=auth_headers(recruitment_accounts['admin_token']),
    )
    assert response.status_code == 409
    assert response.get_json() == {'error': '目前沒有已完成且待結算的 Todo'}


def test_admin_approval_settles_todos_and_accumulates_rewards(
    client,
    app,
    recruitment_accounts,
):
    project_id = add_project(
        app,
        recruitment_accounts['leader_id'],
        title='Settlement project',
        review_status='pending',
    )
    new_coin_todo = add_todo(
        app,
        project_id,
        text='New coin record',
        done=True,
        settled=False,
        claimed_by_id=recruitment_accounts['member_id'],
        priority=0,
        difficulty=13,
        duration=5,
    )
    existing_coin_todo = add_todo(
        app,
        project_id,
        text='Existing coin record',
        done=True,
        settled=False,
        claimed_by_id=recruitment_accounts['outsider_id'],
        priority=4,
        difficulty=2,
        duration=0,
    )
    unclaimed_todo = add_todo(
        app,
        project_id,
        text='Unclaimed task',
        done=True,
        settled=False,
        priority=2,
        difficulty=6,
        duration=1,
    )
    add_todo(app, project_id, text='Still open', done=False, settled=False)
    with app.app_context():
        db.session.add(DailyCheckIn(
            user_id=recruitment_accounts['outsider_id'],
            checkin_date=TODO_REWARD_COIN_DATE,
            points=7,
        ))
        db.session.commit()

    with patch('routes.project_recruitment.project_recruitment.write_todo_settlement_log') as log:
        response = client.post(
            f'/api/admin/project-recruitments/{project_id}/review',
            json={'action': 'approve'},
            headers=auth_headers(recruitment_accounts['admin_token']),
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['review_status'] == 'approved'
    by_id = {todo['id']: todo for todo in payload['todos']}
    assert by_id[new_coin_todo]['settled'] is True
    assert by_id[new_coin_todo]['reward_coins'] == 29
    assert by_id[existing_coin_todo]['settled'] is True
    assert by_id[existing_coin_todo]['reward_coins'] == 7
    assert by_id[unclaimed_todo]['settled'] is True
    assert by_id[unclaimed_todo]['claimed_by_name'] is None
    assert log.call_count == 3
    logged = [call.kwargs for call in log.call_args_list]
    assert {item['status'] for item in logged} == {'success', 'skipped'}
    skipped = next(item for item in logged if item['status'] == 'skipped')
    assert skipped['reason'] == 'missing_claimed_by'
    assert skipped['reward_coins'] == 0
    assert skipped['completed_by_username'] == '-'

    with app.app_context():
        member_coins = DailyCheckIn.query.filter_by(
            user_id=recruitment_accounts['member_id'],
            checkin_date=TODO_REWARD_COIN_DATE,
        ).one()
        outsider_coins = DailyCheckIn.query.filter_by(
            user_id=recruitment_accounts['outsider_id'],
            checkin_date=TODO_REWARD_COIN_DATE,
        ).one()
        assert member_coins.points == 29
        assert outsider_coins.points == 14
        assert db.session.get(Todo, unclaimed_todo).settled is True


@pytest.mark.parametrize(
    ('todo', 'expected'),
    [
        (SimpleNamespace(priority=None, difficulty=None, duration=None), (5, 6, 0, 11)),
        (SimpleNamespace(priority='bad', difficulty='bad', duration='bad'), (5, 6, 0, 11)),
        (SimpleNamespace(priority=-10, difficulty=4, duration=-2), (1, 4, 0, 8)),
        (SimpleNamespace(priority=99, difficulty=99, duration=99), (5, 6, 5, 16)),
    ],
)
def test_reward_breakdown_normalizes_invalid_legacy_values(todo, expected):
    breakdown = get_todo_reward_breakdown(todo)
    level, difficulty, duration, reward = expected
    assert breakdown['priority_level'] == level
    assert breakdown['difficulty'] == difficulty
    assert breakdown['duration'] == duration
    assert breakdown['reward_coins'] == reward
    assert breakdown['reward_formula'].endswith(f'= {reward}')


def test_structured_log_helpers_add_default_metadata():
    with (
        patch.object(recruitment_routes.project_logger, 'info') as project_info,
        patch.object(recruitment_routes.todo_settlement_logger, 'warning') as settlement_warning,
    ):
        recruitment_routes.write_project_log('unknown-level', status='success')
        recruitment_routes.write_todo_settlement_log('warning', status='skipped')

    project_message = project_info.call_args.args[0]
    settlement_message = settlement_warning.call_args.args[0]
    assert '"event": "project_recruitment"' in project_message
    assert '"logged_at":' in project_message
    assert '"event": "todo_settlement"' in settlement_message
    assert '"status": "skipped"' in settlement_message
