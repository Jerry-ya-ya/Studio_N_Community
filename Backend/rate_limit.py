import hashlib

from flask import request
from flask_jwt_extended import get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    headers_enabled=True,
    key_prefix="jack-and-beanstalks",
)


@limiter.request_filter
def active_superadmin_rate_limit_override():
    """Skip only Flask-Limiter checks while the approved override is active."""
    if not request.path.startswith('/api/'):
        return False

    # Import lazily to keep the limiter usable while models are being registered.
    from models import ApiRateLimitOverride, db
    from time_utils import taipei_now

    override = db.session.get(ApiRateLimitOverride, 1)
    return bool(override and override.expires_at > taipei_now())


# Resource-creating member endpoints share one quota so switching endpoints
# cannot bypass the protection. Apply this inside @jwt_required() so its key is
# based on a verified identity rather than attacker-controlled token contents.
MEMBER_WRITE_RATE_LIMIT = "30 per minute"
MEMBER_WRITE_RATE_SCOPE = "member-resource-writes"


def _hashed_request_value(field):
    data = request.get_json(silent=True) or {}
    value = str(data.get(field) or "").strip().casefold()
    if not value:
        return f"missing:{get_remote_address()}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def username_rate_limit_key():
    return f"username:{_hashed_request_value('username')}"


def email_rate_limit_key():
    return f"email:{_hashed_request_value('email')}"


def authenticated_user_rate_limit_key():
    identity = get_jwt_identity()
    if identity is None:
        return f"ip:{get_remote_address()}"
    return f"user:{identity}"


member_write_rate_limited = limiter.shared_limit(
    MEMBER_WRITE_RATE_LIMIT,
    key_func=authenticated_user_rate_limit_key,
    scope=MEMBER_WRITE_RATE_SCOPE,
)


def failed_response(response):
    return response.status_code >= 400
