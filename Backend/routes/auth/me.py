import os

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required, unset_refresh_cookies
from flask_mail import Message
from models import DailyCheckIn, db, User
from routes.auth.email import generate_confirmation_token, mail
from routes.auth.utils import get_current_user_from_token
from time_utils import taipei_now, to_taipei_iso

me_bp = Blueprint('me', __name__)

# GET：取得目前登入使用者資訊
@me_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    user = get_current_user_from_token()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    total_coins = int(db.session.query(
        db.func.coalesce(db.func.sum(DailyCheckIn.points), 0)
    ).filter(DailyCheckIn.user_id == user.id).scalar() or 0)

    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'nickname': user.nickname,
        'github_url': user.github_url,
        'githubUrl': user.github_url,
        'created_at': to_taipei_iso(user.created_at),
        'avatar_url': user.avatar_url,
        'avatar_source': user.avatar_source or 'github',
        'avatarSource': user.avatar_source or 'github',
        'role': user.role,
        'coins': total_coins,
        'total_coins': total_coins,
        'totalCoins': total_coins,
    })

# PUT：更新使用者資訊
@me_bp.route('/me', methods=['PUT'])
@jwt_required()
def update_current_user():
    user = get_current_user_from_token()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json(silent=True) or {}
    new_email = data.get('email')
    email_changed = False

    if new_email is not None:
        new_email = new_email.strip()
        if not new_email:
            return jsonify({'error': 'Email cannot be empty'}), 400

        existing_user = User.query.filter(User.email == new_email, User.id != user.id).first()
        if existing_user:
            return jsonify({'error': 'Email already exists'}), 400

        if new_email != user.email:
            user.email = new_email
            user.email_verified = False
            email_changed = True

    user.nickname = data.get('nickname', user.nickname)
    if 'githubUrl' in data or 'github_url' in data:
        user.github_url = (data.get('githubUrl') or data.get('github_url') or '').strip()[:255] or None
    if 'avatarSource' in data or 'avatar_source' in data:
        avatar_source = (data.get('avatarSource') or data.get('avatar_source') or 'github').strip()
        if avatar_source not in ['local', 'github']:
            return jsonify({'error': 'Avatar source must be local or github'}), 400
        user.avatar_source = avatar_source
    db.session.commit()

    if email_changed:
        token = generate_confirmation_token(user.email)
        api_url = current_app.config.get('API_URL', 'http://localhost:5000').rstrip('/')
        verify_link = f"{api_url}/api/verify-email/{token}"
        sender_email = os.getenv('MAIL_USERNAME')
        msg = Message(
            subject='驗證你的新 Email',
            sender=sender_email,
            recipients=[user.email]
        )
        msg.body = f'請點擊連結完成新 Email 驗證：{verify_link}'
        mail.send(msg)

    return jsonify({
        'message': 'Profile updated',
        'email_verification_required': email_changed
    })

# GET：根據用戶 ID 獲取用戶資料
@me_bp.route('/public/<int:user_id>', methods=['GET'])
@jwt_required()
def public_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用戶不存在'}), 404

    return jsonify({
        'id': user.id,
        'username': user.display_username,
        'nickname': user.display_nickname,
        'github_url': user.github_url,
        'githubUrl': user.github_url,
        'email': user.display_email,
        'avatar_url': user.avatar_url,
        'avatar_source': user.avatar_source or 'github',
        'avatarSource': user.avatar_source or 'github',
        'role': user.role,
        'created_at': to_taipei_iso(user.created_at)
    })


@me_bp.route('/me', methods=['DELETE'])
@jwt_required()
def delete_current_user():
    user = get_current_user_from_token()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.role == 'superadmin':
        return jsonify({'error': 'Superadmin accounts cannot be deleted from settings'}), 403

    data = request.get_json(silent=True) or {}
    if data.get('confirmation') != 'DELETE':
        return jsonify({'error': 'Type DELETE to confirm account deletion'}), 400

    deleted_label = f'deleted_user_{user.id}'
    user.is_deleted = True
    user.deleted_at = taipei_now()
    user.email_verified = False
    user.username = deleted_label
    user.nickname = '已刪除'
    user.email = f'{deleted_label}@deleted.local'
    user.github_url = None
    user.avatar_url = None
    user.avatar_source = 'github'
    db.session.commit()

    response = jsonify({'message': 'Account deleted'})
    unset_refresh_cookies(response)
    return response
