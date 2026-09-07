from datetime import date

from flask_jwt_extended import create_access_token

from models import DailyCheckIn, Post, ProjectRecruitment, Todo, User, UserAchievement, db
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
    achievements = {item['key']: item for item in payload['achievements']}
    assert len(achievements) == 15
    assert achievements['firstCheckIn']['unlocked'] is True
    assert achievements['streakThree']['unlocked'] is True
    assert achievements['firstProject']['unlocked'] is True
    assert achievements['firstTask']['unlocked'] is True
    assert achievements['firstPost']['unlocked'] is True
    assert achievements['socialCircle']['unlocked'] is False


def test_monitored_post_api_persists_unlock_once_and_reports_it(client, app):
    with app.app_context():
        user = User(
            username='achievement-listener-user',
            email='achievement-listener-user@example.com',
            password='test-password',
            email_verified=True,
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        token = create_access_token(identity=str(user_id))

    first_response = client.post(
        '/api/post',
        json={'content': 'The listener should verify this post.'},
        headers={'Authorization': f'Bearer {token}'},
    )
    second_response = client.post(
        '/api/post',
        json={'content': 'Unlock records must remain idempotent.'},
        headers={'Authorization': f'Bearer {token}'},
    )

    assert first_response.status_code == 200
    assert first_response.get_json()['unlockedAchievements'] == ['firstPost']
    assert second_response.status_code == 200
    assert second_response.get_json()['unlockedAchievements'] == []
    with app.app_context():
        assert UserAchievement.query.filter_by(
            user_id=user_id,
            achievement_key='firstPost',
        ).count() == 1


def test_me_backfills_all_eligible_achievements_and_excludes_coin_ledger_from_checkins(client, app):
    with app.app_context():
        user = User(
            username='achievement-backfill-user',
            email='achievement-backfill-user@example.com',
            password='test-password',
            email_verified=True,
        )
        friends = [
            User(
                username=f'achievement-friend-{index}',
                email=f'achievement-friend-{index}@example.com',
                password='test-password',
                email_verified=True,
            )
            for index in range(5)
        ]
        db.session.add_all([user, *friends])
        db.session.flush()
        user.friends.extend(friends)
        db.session.add_all([
            DailyCheckIn(
                user_id=user.id,
                checkin_date=date(2026, 1, day),
                points=4,
            )
            for day in range(1, 31)
        ])
        # Todo rewards are stored in this legacy row. Its points count as coins,
        # while its sentinel date must never count as a daily check-in.
        db.session.add(DailyCheckIn(
            user_id=user.id,
            checkin_date=date(1970, 1, 1),
            points=10,
        ))
        db.session.add_all([
            ProjectRecruitment(
                title=f'Backfill project {index}',
                summary='Achievement verification fixture.',
                creator_id=user.id,
                token_used=100,
            )
            for index in range(5)
        ])
        db.session.add_all([
            Todo(text=f'Completed {index}', claimed_by_id=user.id, done=True)
            for index in range(10)
        ])
        db.session.add(Post(content='Backfill post', user_id=user.id))
        db.session.commit()
        user_id = user.id
        token = create_access_token(identity=str(user_id))

    response = client.get('/api/me', headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['coins'] == 130
    assert payload['achievementStats']['totalCheckIns'] == 30
    assert payload['achievementStats']['longestCheckInStreak'] == 30
    assert all(item['unlocked'] for item in payload['achievements'])
    with app.app_context():
        assert UserAchievement.query.filter_by(user_id=user_id).count() == 15
