from secrets import compare_digest

from flask import Blueprint, abort, current_app, request
from models import db, User, UserAchievement

test_utils = Blueprint('test_utils', __name__)


@test_utils.before_request
def require_e2e_test_token():
    expected = current_app.config.get("E2E_TEST_TOKEN") or ""
    if len(expected) < 32:
        abort(404)

    provided = request.headers.get("X-E2E-Test-Token", "")
    if not compare_digest(provided.encode("utf-8"), expected.encode("utf-8")):
        abort(403)


@test_utils.route('/test/clear-db', methods=['POST'])
def clear_db():
    UserAchievement.query.delete()
    User.query.delete()
    db.session.commit()
    return {'status': 'cleared'}

@test_utils.route('/test/verify-user', methods=['POST'])
def verify_user():
    data = request.json
    user = User.query.filter_by(email=data['email']).first()
    if user:
        user.email_verified = True
        db.session.commit()
    return {"status": "verified"}
