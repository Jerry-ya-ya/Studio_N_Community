from datetime import datetime, timezone
from uuid import uuid4

from flask_jwt_extended import create_refresh_token, decode_token

from models import RefreshToken, db
from time_utils import taipei_now


def _expires_at(jwt_payload):
    return datetime.fromtimestamp(jwt_payload['exp'], timezone.utc).replace(tzinfo=None)


def issue_refresh_token(user, remember_me, expires_delta, family_id=None):
    """Issue and persist a refresh token before it is sent to the client."""
    family_id = family_id or str(uuid4())
    encoded_token = create_refresh_token(
        identity=str(user.id),
        additional_claims={
            'role': user.role,
            'remember_me': remember_me,
            'family_id': family_id,
        },
        expires_delta=expires_delta,
    )
    payload = decode_token(encoded_token)
    record = RefreshToken(
        jti=payload['jti'],
        family_id=family_id,
        user_id=user.id,
        expires_at=_expires_at(payload),
    )
    db.session.add(record)
    return encoded_token, record


def revoke_token(record, replaced_by_jti=None):
    if record.revoked_at is None:
        record.revoked_at = taipei_now()
    if replaced_by_jti is not None:
        record.replaced_by_jti = replaced_by_jti


def revoke_family(family_id):
    RefreshToken.query.filter(
        RefreshToken.family_id == family_id,
        RefreshToken.revoked_at.is_(None),
    ).update({'revoked_at': taipei_now()}, synchronize_session=False)


def revoke_all_user_tokens(user_id):
    RefreshToken.query.filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked_at.is_(None),
    ).update({'revoked_at': taipei_now()}, synchronize_session=False)


def is_refresh_token_revoked(jwt_payload):
    """Reject refresh tokens that were never issued here or are no longer active."""
    if jwt_payload.get('type') != 'refresh':
        return False

    record = RefreshToken.query.filter_by(jti=jwt_payload.get('jti')).first()
    return record is None or record.revoked_at is not None
