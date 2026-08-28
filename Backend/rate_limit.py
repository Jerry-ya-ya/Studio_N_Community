import hashlib

from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    headers_enabled=True,
    key_prefix="jack-and-beanstalks",
)


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


def failed_response(response):
    return response.status_code >= 400
