import json
from datetime import timedelta

from flask import Blueprint, g, jsonify, request

from log_writer import get_backend_logger
from models import ApiRateLimitOverride, db
from routes.admin.decorators import superadmin_required
from time_utils import taipei_now, to_taipei_iso


special_abilities_bp = Blueprint('special_abilities', __name__)
security_logger = get_backend_logger('security', 'security.log', message_only=True)
MIN_OVERRIDE_MINUTES = 10
MAX_OVERRIDE_MINUTES = 30
OVERRIDE_ID = 1


def serialize_override(override, now=None):
    now = now or taipei_now()
    active = bool(override and override.expires_at > now)
    remaining_seconds = (
        max(0, int((override.expires_at - now).total_seconds())) if active else 0
    )
    return {
        'active': active,
        'activatedAt': to_taipei_iso(override.activated_at) if override else None,
        'expiresAt': to_taipei_iso(override.expires_at) if active else None,
        'remainingSeconds': remaining_seconds,
        'minimumMinutes': MIN_OVERRIDE_MINUTES,
        'maximumMinutes': MAX_OVERRIDE_MINUTES,
    }


@special_abilities_bp.route('/superadmin/special-abilities/api-rate-limit', methods=['GET'])
@superadmin_required
def get_api_rate_limit_override():
    response = jsonify(serialize_override(db.session.get(ApiRateLimitOverride, OVERRIDE_ID)))
    response.headers['Cache-Control'] = 'no-store'
    return response


@special_abilities_bp.route('/superadmin/special-abilities/api-rate-limit', methods=['POST'])
@superadmin_required
def activate_api_rate_limit_override():
    data = request.get_json(silent=True) or {}
    duration_minutes = data.get('durationMinutes')
    if type(duration_minutes) is not int or not (
        MIN_OVERRIDE_MINUTES <= duration_minutes <= MAX_OVERRIDE_MINUTES
    ):
        return jsonify({
            'error': f'解除時間必須介於 {MIN_OVERRIDE_MINUTES} 到 {MAX_OVERRIDE_MINUTES} 分鐘',
            'code': 'invalid_duration',
        }), 400

    now = taipei_now()
    override = db.session.get(ApiRateLimitOverride, OVERRIDE_ID)
    if override is None:
        override = ApiRateLimitOverride(id=OVERRIDE_ID)
        db.session.add(override)

    override.activated_at = now
    override.expires_at = now + timedelta(minutes=duration_minutes)
    override.activated_by_id = g.current_user.id
    db.session.commit()

    security_logger.warning(json.dumps({
        'event': 'api_rate_limit_override',
        'status': 'activated',
        'superadmin_id': g.current_user.id,
        'username': g.current_user.display_username,
        'duration_minutes': duration_minutes,
        'activated_at': to_taipei_iso(override.activated_at),
        'expires_at': to_taipei_iso(override.expires_at),
    }, ensure_ascii=False))

    response = jsonify(serialize_override(override, now))
    response.headers['Cache-Control'] = 'no-store'
    return response
