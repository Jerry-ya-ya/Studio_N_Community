from flask import Blueprint, request
from models import db, User, UserAchievement

test_utils = Blueprint('test_utils', __name__)

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
