from flask import Blueprint, current_app, jsonify, request
from flask_mail import Mail, Message
import os
from flask_jwt_extended import create_access_token
from models import db, User

from itsdangerous import URLSafeTimedSerializer
from flask_limiter.util import get_remote_address
from rate_limit import limiter, email_rate_limit_key

email_bp = Blueprint('email', __name__)

mail = Mail()

def init_mail(app):
    server = os.getenv("MAIL_SERVER")
    port = os.getenv("MAIL_PORT")
    username = os.getenv("MAIL_USERNAME")
    password = os.getenv("MAIL_PASSWORD")

    app.config['MAIL_SERVER'] = server
    app.config['MAIL_PORT'] = port
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = username
    app.config['MAIL_PASSWORD'] = password

    mail.init_app(app)

def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(current_app.config['JWT_SECRET_KEY'])
    return serializer.dumps(email, salt='email-confirm')

def confirm_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(current_app.config['JWT_SECRET_KEY'])
    try:
        return serializer.loads(token, salt='email-confirm', max_age=expiration)
    except Exception:
        return None

@email_bp.route('/verify-email/<token>')
def verify_email(token):
    email = confirm_token(token)
    if not email:
        return jsonify({'error': '驗證連結無效或已過期'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': '用戶不存在'}), 404

    if user.email_verified:
        return jsonify({'error': '此郵箱已經驗證過了'}), 400

    user.email_verified = True
    db.session.commit()

    # 生成 access token
    access_token = create_access_token(identity=str(user.id), additional_claims={'role': user.role})
    
    return jsonify({
        'message': 'Email 驗證成功',
        'access_token': access_token,
        'username': user.username,
        'role': user.role,
        'user_id': user.id
    })

@email_bp.route('/resendverification', methods=['POST'])
@limiter.limit("5 per hour", key_func=get_remote_address)
@limiter.limit("3 per hour", key_func=email_rate_limit_key)
def resend_verification():
    data = request.get_json(silent=True) or {}
    email = data.get('email')

    if not email:
        return jsonify({'error': '請填寫 Email'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'Email 不存在'}), 404
    if user.email_verified:
        return jsonify({'message': '此帳號已驗證，無需重寄'}), 200

    token = generate_confirmation_token(email)
    base_url = current_app.config.get('API_URL', 'http://localhost:5000').rstrip('/')
    link = f"{base_url}/api/verify-email/{token}"

    msg = Message('重新寄送帳號驗證信', sender='jerry0907zheng@gmail.com', recipients=[email])
    msg.body = f'請點擊以下連結完成帳號驗證：{link}'
    mail.send(msg)

    return jsonify({'message': '驗證信已重新寄送'})
