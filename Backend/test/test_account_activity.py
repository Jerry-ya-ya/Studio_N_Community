from datetime import date, datetime
from uuid import uuid4

from flask_jwt_extended import create_access_token

from account_activity import deactivate_inactive_users
from models import DailyCheckIn, ProjectRecruitment, ProjectRecruitmentMember, Todo, User, db
from routes.check_in import check_in as check_in_module


def test_seven_days_without_check_in_deactivates_and_releases_all_claims(app):
    suffix = uuid4().hex
    with app.app_context():
        leader = User(
            username=f'activity-leader-{suffix}',
            email=f'activity-leader-{suffix}@example.com',
            password='test-password',
            created_at=datetime(2026, 9, 10),
        )
        stale_user = User(
            username=f'activity-stale-{suffix}',
            email=f'activity-stale-{suffix}@example.com',
            password='test-password',
            created_at=datetime(2026, 8, 1),
        )
        db.session.add_all([leader, stale_user])
        db.session.flush()
        project = ProjectRecruitment(
            title='Activity cleanup project',
            summary='Exercises inactivity cleanup.',
            creator_id=leader.id,
        )
        db.session.add(project)
        db.session.flush()
        outstanding_todo = Todo(
            text='Outstanding task',
            project_id=project.id,
            claimed_by_id=stale_user.id,
        )
        settled_todo = Todo(
            text='Settled task',
            project_id=project.id,
            claimed_by_id=stale_user.id,
            done=True,
            settled=True,
        )
        db.session.add_all([
            ProjectRecruitmentMember(project_id=project.id, user_id=stale_user.id),
            outstanding_todo,
            settled_todo,
            DailyCheckIn(
                user_id=stale_user.id,
                checkin_date=date(2026, 9, 4),
                points=1,
            ),
        ])
        db.session.commit()
        stale_user_id = stale_user.id
        leader_id = leader.id
        project_id = project.id
        todo_ids = [outstanding_todo.id, settled_todo.id]

        result = deactivate_inactive_users(datetime(2026, 9, 11, 0, 5))

        assert stale_user_id in result['user_ids']
        assert leader_id not in result['user_ids']
        assert db.session.get(User, stale_user_id).is_active is False
        assert ProjectRecruitmentMember.query.filter_by(user_id=stale_user_id).count() == 0
        assert all(db.session.get(Todo, todo_id).claimed_by_id is None for todo_id in todo_ids)

        Todo.query.filter_by(project_id=project_id).delete()
        ProjectRecruitment.query.filter_by(id=project_id).delete()
        DailyCheckIn.query.filter_by(user_id=stale_user_id).delete()
        User.query.filter(User.id.in_([leader_id, stale_user_id])).delete(
            synchronize_session=False
        )
        db.session.commit()


def test_accounts_inside_seven_day_window_and_synthetic_rewards_stay_active(app):
    suffix = uuid4().hex
    with app.app_context():
        recent_user = User(
            username=f'activity-recent-{suffix}',
            email=f'activity-recent-{suffix}@example.com',
            password='test-password',
            created_at=datetime(2026, 8, 1),
        )
        db.session.add(recent_user)
        db.session.flush()
        db.session.add_all([
            DailyCheckIn(user_id=recent_user.id, checkin_date=date(1970, 1, 1), points=20),
            DailyCheckIn(user_id=recent_user.id, checkin_date=date(2026, 9, 5), points=1),
        ])
        db.session.commit()
        user_id = recent_user.id

        result = deactivate_inactive_users(datetime(2026, 9, 11, 23, 59))

        assert user_id not in result['user_ids']
        assert db.session.get(User, user_id).is_active is True

        DailyCheckIn.query.filter_by(user_id=user_id).delete()
        User.query.filter_by(id=user_id).delete()
        db.session.commit()


def test_check_in_cleans_up_then_reactivates_returning_user(app, client, monkeypatch):
    suffix = uuid4().hex
    now = datetime(2026, 9, 11, 9, 0)
    monkeypatch.setattr(check_in_module, 'taipei_now', lambda: now)

    with app.app_context():
        leader = User(
            username=f'activity-api-leader-{suffix}',
            email=f'activity-api-leader-{suffix}@example.com',
            password='test-password',
            created_at=datetime(2026, 9, 10),
        )
        stale_user = User(
            username=f'activity-api-stale-{suffix}',
            email=f'activity-api-stale-{suffix}@example.com',
            password='test-password',
            created_at=datetime(2026, 8, 1),
        )
        db.session.add_all([leader, stale_user])
        db.session.flush()
        project = ProjectRecruitment(
            title='Activity API project',
            summary='Exercises check-in cleanup.',
            creator_id=leader.id,
        )
        db.session.add(project)
        db.session.flush()
        todo = Todo(
            text='Claim released by check-in',
            project_id=project.id,
            claimed_by_id=stale_user.id,
        )
        db.session.add_all([
            ProjectRecruitmentMember(project_id=project.id, user_id=stale_user.id),
            todo,
            DailyCheckIn(
                user_id=stale_user.id,
                checkin_date=date(2026, 9, 4),
                points=1,
            ),
        ])
        db.session.commit()
        token = create_access_token(identity=str(stale_user.id))
        stale_user_id = stale_user.id
        leader_id = leader.id
        project_id = project.id
        todo_id = todo.id

    response = client.post(
        '/api/check-in',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 201
    with app.app_context():
        assert db.session.get(User, stale_user_id).is_active is True
        assert ProjectRecruitmentMember.query.filter_by(user_id=stale_user_id).count() == 0
        assert db.session.get(Todo, todo_id).claimed_by_id is None
        assert DailyCheckIn.query.filter_by(
            user_id=stale_user_id,
            checkin_date=now.date(),
        ).count() == 1

        Todo.query.filter_by(project_id=project_id).delete()
        ProjectRecruitment.query.filter_by(id=project_id).delete()
        DailyCheckIn.query.filter_by(user_id=stale_user_id).delete()
        User.query.filter(User.id.in_([leader_id, stale_user_id])).delete(
            synchronize_session=False
        )
        db.session.commit()
