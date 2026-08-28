from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from werkzeug.security import generate_password_hash, check_password_hash
from models import db
from routes.auth.utils import get_current_user_from_token
from password_policy import password_error_response

changepassword_bp = Blueprint('changepassword', __name__)

@changepassword_bp.route('/changepassword', methods=['PUT'])
@jwt_required()
def changepassword():
    user = get_current_user_from_token()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json(silent=True) or {}
    old_pw = data.get('old_password')
    new_pw = data.get('new_password')

    if not all([old_pw, new_pw]):
        return jsonify({'error': '請填寫舊密碼和新密碼'}), 400

    if not check_password_hash(user.password, old_pw):
        return jsonify({'error': '舊密碼錯誤'}), 400

    password_error = password_error_response(
        new_pw,
        username=user.username,
        email=user.email,
    )
    if password_error:
        return jsonify(password_error), 400

    user.password = generate_password_hash(new_pw)
    db.session.commit()

    return jsonify({'message': '密碼修改成功'})
