from datetime import date, datetime, timedelta

from models import DailyCheckIn, ProjectRecruitmentMember, Todo, User, db
from time_utils import taipei_now


INACTIVITY_DAYS = 7
# Project task rewards are stored as synthetic check-ins on 1970-01-01. They
# represent coins rather than attendance and must not keep an account active.
FIRST_REAL_CHECK_IN_DATE = date(2000, 1, 1)


def _reference_date(reference_time=None):
    value = reference_time or taipei_now()
    return value.date() if isinstance(value, datetime) else value


def deactivate_inactive_users(reference_time=None, commit=True):
    """Deactivate users with no check-in for seven days and release their work.

    Users who have never checked in receive the same grace period from account
    creation. Every claimed task is released when an account becomes inactive,
    including settled tasks, as the account must abandon all of its claims.
    """
    cutoff = _reference_date(reference_time) - timedelta(days=INACTIVITY_DAYS)
    latest_rows = (
        db.session.query(
            DailyCheckIn.user_id,
            db.func.max(DailyCheckIn.checkin_date),
        )
        .filter(DailyCheckIn.checkin_date >= FIRST_REAL_CHECK_IN_DATE)
        .group_by(DailyCheckIn.user_id)
        .all()
    )
    latest_check_ins = dict(latest_rows)

    inactive_user_ids = []
    for user in User.query.filter_by(is_active=True, is_deleted=False).all():
        last_active_date = latest_check_ins.get(user.id)
        if last_active_date is None and user.created_at is not None:
            last_active_date = user.created_at.date()

        if last_active_date is not None and last_active_date <= cutoff:
            user.is_active = False
            inactive_user_ids.append(user.id)

    memberships_removed = 0
    tasks_released = 0
    if inactive_user_ids:
        memberships_removed = (
            ProjectRecruitmentMember.query
            .filter(ProjectRecruitmentMember.user_id.in_(inactive_user_ids))
            .delete(synchronize_session=False)
        )
        tasks_released = (
            Todo.query
            .filter(Todo.claimed_by_id.in_(inactive_user_ids))
            .update({Todo.claimed_by_id: None}, synchronize_session=False)
        )

    if commit:
        db.session.commit()

    return {
        'deactivated': len(inactive_user_ids),
        'memberships_removed': memberships_removed,
        'tasks_released': tasks_released,
        'user_ids': inactive_user_ids,
    }
