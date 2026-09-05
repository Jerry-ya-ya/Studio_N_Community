from datetime import date

from flask_jwt_extended import create_access_token

from models import DailyCheckIn, Post, ProjectRecruitment, Todo, User, db
from routes.auth.me import calculate_longest_checkin_streak


def test_calculate_longest_checkin_streak_handles_gaps_and_duplicates():
    assert calculate_longest_checkin_streak([]) == 0
    assert calculate_longest_checkin_streak([
        date(2026, 1, 5),
        date(2026, 1, 1),
        date(2026, 1, 2),
        date(2026, 1, 2),
        date(2026, 1, 3),
    ]) == 3


def test_me_returns_achievement_progress_statistics(client, app):
    with app.app_context():
        user = User(
            username='achievement-stats-user',
            email='achievement-stats-user@example.com',
            password='test-password',
            email_verified=True,
        )
        friend = User(
            username='achievement-stats-friend',
            email='achievement-stats-friend@example.com',
            password='test-password',
            email_verified=True,
        )
        db.session.add_all([user, friend])
        db.session.flush()
        user.friends.append(friend)

        db.session.add_all([
            DailyCheckIn(user_id=user.id, checkin_date=date(2026, 1, 1), points=2),
            DailyCheckIn(user_id=user.id, checkin_date=date(2026, 1, 2), points=3),
            DailyCheckIn(user_id=user.id, checkin_date=date(2026, 1, 3), points=5),
            DailyCheckIn(user_id=user.id, checkin_date=date(2026, 1, 5), points=1),
            ProjectRecruitment(
                title='Achievement project one',
                summary='First project used to calculate achievement progress.',
                creator_id=user.id,
                token_used=100,
            ),
            ProjectRecruitment(
                title='Achievement project two',
                summary='Second project used to calculate achievement progress.',
                creator_id=user.id,
                token_used=35,
            ),
            Todo(text='Finished task', claimed_by_id=user.id, done=True),
            Todo(text='Open task', claimed_by_id=user.id, done=False),
            Post(content='Achievement test post', user_id=user.id),
        ])
        db.session.commit()
        token = create_access_token(identity=str(user.id))

    response = client.get(
        '/api/me',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['coins'] == 11
    assert payload['achievementStats'] == {
        'totalCheckIns': 4,
        'longestCheckInStreak': 3,
        'createdProjects': 2,
        'projectTokensUsed': 135,
        'completedTodos': 1,
        'createdPosts': 1,
        'friends': 1,
    }
