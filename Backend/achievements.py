"""Central server-side achievement catalogue, verification, and API listener."""

from dataclasses import dataclass
from datetime import date

from flask import current_app, g, jsonify, request
from flask_jwt_extended import get_jwt_identity

from models import DailyCheckIn, Post, ProjectRecruitment, Todo, User, UserAchievement, db
from time_utils import to_taipei_iso


@dataclass(frozen=True)
class AchievementDefinition:
    key: str
    stat: str
    target: int


# This is the canonical backend definition of all achievements. Clients may render
# this data, but they do not decide whether an achievement has been earned.
ACHIEVEMENTS = (
    AchievementDefinition('firstCheckIn', 'totalCheckIns', 1),
    AchievementDefinition('checkInWeek', 'totalCheckIns', 7),
    AchievementDefinition('checkInMonth', 'totalCheckIns', 30),
    AchievementDefinition('streakThree', 'longestCheckInStreak', 3),
    AchievementDefinition('streakWeek', 'longestCheckInStreak', 7),
    AchievementDefinition('streakMonth', 'longestCheckInStreak', 30),
    AchievementDefinition('firstProject', 'createdProjects', 1),
    AchievementDefinition('projectBuilder', 'createdProjects', 5),
    AchievementDefinition('tokenSpender', 'projectTokensUsed', 100),
    AchievementDefinition('tokenMaster', 'projectTokensUsed', 500),
    AchievementDefinition('firstTask', 'completedTodos', 1),
    AchievementDefinition('taskMaster', 'completedTodos', 10),
    AchievementDefinition('firstPost', 'createdPosts', 1),
    AchievementDefinition('socialCircle', 'friends', 5),
    AchievementDefinition('firstPotOfGold', 'coins', 100),
)


# Endpoint names are stable Flask identifiers, so validation cannot be bypassed by
# adding a second URL for the same view. Values indicate whether the authenticated
# caller is affected; routes can queue additional affected users through g.
MONITORED_ENDPOINTS = {
    'check_in.create_check_in': True,
    'project_recruitment.create_project_recruitment': True,
    'todo.add_todo': True,
    'todo.update_todo': True,
    'post.create_post': True,
    'friend_bp.accept_friend_request': True,
    'project_recruitment.review_project_recruitment': False,
}


def calculate_longest_checkin_streak(checkin_dates):
    """Return the longest run of consecutive dates in a check-in history."""
    longest = 0
    current = 0
    previous = None

    for checkin_date in sorted(set(checkin_dates)):
        if previous and (checkin_date - previous).days == 1:
            current += 1
        else:
            current = 1
        longest = max(longest, current)
        previous = checkin_date

    return longest


def get_achievement_stats(user):
    # The 1970 record is a legacy coin ledger entry used by todo settlement, not a
    # real daily check-in. It contributes coins but not check-in milestones.
    checkin_dates = [
        row[0]
        for row in db.session.query(DailyCheckIn.checkin_date)
        .filter(
            DailyCheckIn.user_id == user.id,
            DailyCheckIn.checkin_date != date(1970, 1, 1),
        )
        .order_by(DailyCheckIn.checkin_date.asc())
        .all()
    ]
    project_tokens_used = int(db.session.query(
        db.func.coalesce(db.func.sum(ProjectRecruitment.token_used), 0)
    ).filter(ProjectRecruitment.creator_id == user.id).scalar() or 0)
    coins = int(db.session.query(
        db.func.coalesce(db.func.sum(DailyCheckIn.points), 0)
    ).filter(DailyCheckIn.user_id == user.id).scalar() or 0)

    return {
        'coins': coins,
        'totalCheckIns': len(checkin_dates),
        'longestCheckInStreak': calculate_longest_checkin_streak(checkin_dates),
        'createdProjects': ProjectRecruitment.query.filter_by(creator_id=user.id).count(),
        'projectTokensUsed': project_tokens_used,
        'completedTodos': Todo.query.filter(
            Todo.claimed_by_id == user.id,
            Todo.done.is_(True),
        ).count(),
        'createdPosts': Post.query.filter_by(user_id=user.id).count(),
        'friends': len(user.friends),
    }


def evaluate_achievements(user, commit=True):
    """Verify all milestones and persist newly unlocked records exactly once."""
    stats = get_achievement_stats(user)
    records = {
        record.achievement_key: record
        for record in UserAchievement.query.filter_by(user_id=user.id).all()
    }
    newly_unlocked = []

    for definition in ACHIEVEMENTS:
        if definition.key in records or stats[definition.stat] < definition.target:
            continue
        record = UserAchievement(user_id=user.id, achievement_key=definition.key)
        db.session.add(record)
        records[definition.key] = record
        newly_unlocked.append(record)

    if newly_unlocked:
        db.session.flush()
        if commit:
            db.session.commit()

    return stats, records, newly_unlocked


def serialize_achievements(stats, records):
    return [
        {
            'key': definition.key,
            'stat': definition.stat,
            'target': definition.target,
            'progress': stats[definition.stat],
            'unlocked': definition.key in records,
            'unlockedAt': (
                to_taipei_iso(records[definition.key].unlocked_at)
                if definition.key in records else None
            ),
        }
        for definition in ACHIEVEMENTS
    ]


def queue_achievement_check(*user_ids):
    """Mark additional users affected by the current API for post-response checks."""
    queued = getattr(g, 'achievement_user_ids', set())
    queued.update(user_id for user_id in user_ids if user_id is not None)
    g.achievement_user_ids = queued


def _current_user_id():
    try:
        identity = get_jwt_identity()
    except RuntimeError:
        return None
    identity_text = str(identity or '')
    if identity_text.isdigit():
        return int(identity_text)
    user = User.query.filter_by(username=identity_text).first()
    return user.id if user else None


def _add_unlocks_to_response(response, unlocked):
    payload = response.get_json(silent=True)
    if not isinstance(payload, dict):
        return response
    payload['unlockedAchievements'] = [record.achievement_key for record in unlocked]
    response.set_data(jsonify(payload).get_data())
    response.content_type = 'application/json'
    return response


def init_achievement_listener(app):
    """Validate achievements after successful APIs that can change progress."""
    @app.after_request
    def verify_api_achievements(response):
        include_actor = MONITORED_ENDPOINTS.get(request.endpoint)
        if include_actor is None or response.status_code >= 400:
            return response

        user_ids = set(getattr(g, 'achievement_user_ids', set()))
        if include_actor:
            actor_id = _current_user_id()
            if actor_id is not None:
                user_ids.add(actor_id)

        actor_unlocks = []
        actor_id = _current_user_id()
        try:
            for user_id in user_ids:
                user = db.session.get(User, user_id)
                if not user or user.is_deleted:
                    continue
                _, _, newly_unlocked = evaluate_achievements(user, commit=False)
                if user_id == actor_id:
                    actor_unlocks.extend(newly_unlocked)
            if user_ids:
                db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Achievement verification failed')
            return response

        return _add_unlocks_to_response(response, actor_unlocks)

    return verify_api_achievements
