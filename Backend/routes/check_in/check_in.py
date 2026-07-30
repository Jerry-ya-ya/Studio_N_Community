from datetime import timedelta

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from models import DailyCheckIn, db
from routes.auth.utils import get_current_user_from_token
from time_utils import taipei_now, to_taipei_iso

check_in_bp = Blueprint('check_in', __name__)


def today_info():
    today = taipei_now().date()
    is_weekend = today.weekday() >= 5
    return today, is_weekend, 5 if is_weekend else 1


def get_total_points(user_id):
    total = db.session.query(db.func.coalesce(db.func.sum(DailyCheckIn.points), 0)).filter(
        DailyCheckIn.user_id == user_id
    ).scalar()
    return int(total or 0)


def get_last_seven_days(user_id, today):
    start_date = today - timedelta(days=6)
    check_ins = DailyCheckIn.query.filter(
        DailyCheckIn.user_id == user_id,
        DailyCheckIn.checkin_date >= start_date,
        DailyCheckIn.checkin_date <= today,
    ).all()
    checked_dates = {check_in.checkin_date for check_in in check_ins}

    days = []
    for day_offset in range(7):
        date = start_date + timedelta(days=day_offset)
        days.append({
            'date': date.isoformat(),
            'checked': date in checked_dates,
            'points': 5 if date.weekday() >= 5 else 1,
        })

    return {
        'checkedDays': len(checked_dates),
        'totalDays': 7,
        'days': days,
    }


def serialize_status(user, today=None, is_weekend=None, today_points=None):
    today = today or taipei_now().date()
    if is_weekend is None or today_points is None:
        today, is_weekend, today_points = today_info()

    check_in = DailyCheckIn.query.filter_by(user_id=user.id, checkin_date=today).first()

    return {
        'checkedInToday': bool(check_in),
        'today': today.isoformat(),
        'todayPoints': today_points,
        'isWeekend': is_weekend,
        'totalPoints': get_total_points(user.id),
        'lastCheckIn': to_taipei_iso(check_in.created_at) if check_in else None,
        'lastSevenDays': get_last_seven_days(user.id, today),
    }


@check_in_bp.route('/check-in/status', methods=['GET'])
@jwt_required()
def get_check_in_status():
    user = get_current_user_from_token()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify(serialize_status(user))


@check_in_bp.route('/check-in', methods=['POST'])
@jwt_required()
def create_check_in():
    user = get_current_user_from_token()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    today, is_weekend, points = today_info()
    existing = DailyCheckIn.query.filter_by(user_id=user.id, checkin_date=today).first()
    if existing:
        return jsonify({
            **serialize_status(user, today, is_weekend, points),
            'message': 'already checked in today',
        }), 200

    check_in = DailyCheckIn(user_id=user.id, checkin_date=today, points=points)
    db.session.add(check_in)
    db.session.commit()

    return jsonify({
        **serialize_status(user, today, is_weekend, points),
        'earnedPoints': points,
        'message': 'checked in',
    }), 201
