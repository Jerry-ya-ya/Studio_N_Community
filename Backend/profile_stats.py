from models import DailyCheckIn, db

EXPERIENCE_PER_LEVEL = 100


def calculate_level(experience):
    """Return a one-based level for a cumulative experience total."""
    return max(int(experience or 0), 0) // EXPERIENCE_PER_LEVEL + 1


def get_coin_balances(users):
    """Return persisted coin balances for a collection of users in one query."""
    user_ids = [user.id for user in users]
    if not user_ids:
        return {}

    rows = (
        db.session.query(
            DailyCheckIn.user_id,
            db.func.coalesce(db.func.sum(DailyCheckIn.points), 0),
        )
        .filter(DailyCheckIn.user_id.in_(user_ids))
        .group_by(DailyCheckIn.user_id)
        .all()
    )
    return {user_id: int(coins or 0) for user_id, coins in rows}


def serialize_profile_stats(user, coins=0):
    return {
        'pm_level': int(user.pm_level or 1),
        'review_level': int(user.review_level or 1),
        'pm_experience': int(user.pm_experience or 0),
        'review_experience': int(user.review_experience or 0),
        'coins': int(coins or 0),
    }
