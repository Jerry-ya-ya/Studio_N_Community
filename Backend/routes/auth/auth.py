from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity, jwt_required
from models import db, User
from routes.auth.email import generate_confirmation_token, mail
from flask_mail import Message
import os
import json
from flask import current_app
from log_writer import get_backend_logger
from time_utils import taipei_now, to_taipei_iso
from datetime import timedelta
from flask_limiter.util import get_remote_address
from rate_limit import limiter, username_rate_limit_key, email_rate_limit_key, failed_response

auth_bp = Blueprint('auth', __name__)
register_logger = get_backend_logger('register', 'register.log', message_only=True)
sign_in_logger = get_backend_logger('sign_in', 'sign_in.log', message_only=True)


def write_register_log(level, **payload):
    payload.setdefault('event', 'register')
    payload.setdefault('logged_at', to_taipei_iso(taipei_now()))
    log_method = getattr(register_logger, level, register_logger.info)
    log_method(json.dumps(payload, ensure_ascii=False))


def write_sign_in_log(level, **payload):
    payload.setdefault('event', 'sign_in')
    payload.setdefault('logged_at', to_taipei_iso(taipei_now()))
    log_method = getattr(sign_in_logger, level, sign_in_logger.info)
    log_method(json.dumps(payload, ensure_ascii=False))

# 註冊新用戶
@auth_bp.route('/register', methods=['POST'])
@limiter.limit("5 per hour", key_func=get_remote_address)
@limiter.limit("3 per hour", key_func=email_rate_limit_key)
def register():
    data = request.get_json(silent=True) or {}

    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    nickname = data.get('nickname')
    created_at = taipei_now()
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()

    if not all([username, password, email]):
        write_register_log(
            'warning',
            status='failed',
            reason='missing_required_fields',
            username=username or '-',
            email=email or '-',
            nickname=nickname or '-',
            role='-',
            ip=client_ip
        )
        return jsonify({'error': '請填寫所有必填欄位'}), 400

    hashed_pw = generate_password_hash(password)

    if User.query.filter_by(username=username).first():
        write_register_log(
            'warning',
            status='failed',
            reason='username_exists',
            username=username,
            email=email,
            nickname=nickname or '-',
            role='-',
            ip=client_ip
        )
        return jsonify({'error': 'Username already exists'}), 400
    
    if User.query.filter_by(email=email).first():
        write_register_log(
            'warning',
            status='failed',
            reason='email_exists',
            username=username,
            email=email,
            nickname=nickname or '-',
            role='-',
            ip=client_ip
        )
        return jsonify({'error': 'Email already exists'}), 400

    # 判斷是否是唯一超管 email
    if email == current_app.config['SUPERADMIN_EMAIL']:
        role = 'superadmin'
    else:
        role = 'user'
    
    new_user = User(
        username=username,
        password=hashed_pw,
        email=email,
        nickname=nickname,
        email_verified=False,  # 確保新用戶的 email_verified 為 False
        role=role,
        created_at=created_at
    )

    db.session.add(new_user)
    db.session.commit()
    write_register_log(
        'info',
        status='success',
        reason='created',
        user_id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        nickname=new_user.nickname or '-',
        role=new_user.role,
        ip=client_ip,
        created_at=to_taipei_iso(new_user.created_at)
    )

    # 生成確認令牌並發送驗證郵件
    token = generate_confirmation_token(email)
    api_url = current_app.config.get('API_URL', 'http://localhost:5000').rstrip('/')
    verify_link = f"{api_url}/api/verify-email/{token}"
    
    # 使用環境變數中的郵件地址
    sender_email = os.getenv('MAIL_USERNAME')
    msg = Message(
        subject='驗證你的帳號',
        sender=sender_email,
        recipients=[email]
    )
    msg.body = f'請點擊連結完成驗證：{verify_link}'
    mail.send(msg)
        
    return jsonify({
        'message': '註冊成功，請檢查您的郵箱完成驗證',
        'email': email,
        'is_verified': False,  # 明確標示用戶尚未驗證
        'require_verification': True,  # 告訴前端需要驗證
        'role': role,
        'created_at': to_taipei_iso(created_at)
    }), 201

# 登入功能
@auth_bp.route('/login', methods=['POST'])
@limiter.limit("20 per minute", key_func=get_remote_address)
@limiter.limit("5 per 15 minutes", key_func=username_rate_limit_key, deduct_when=failed_response)
def login():
    data = request.get_json(silent=True) or {}

    username = data.get('username')
    password = data.get('password')
    remember_me = bool(data.get('remember_me'))
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()

    if not all([username, password]):
        write_sign_in_log(
            'warning',
            status='failed',
            reason='missing_required_fields',
            username=username or '-',
            role='-',
            remember_me=remember_me,
            ip=client_ip
        )
        return jsonify({'error': '請填寫帳號和密碼'}), 400
    
    user = User.query.filter_by(username=username).first()
        
    if not user or user.is_deleted or not check_password_hash(user.password, password):
        write_sign_in_log(
            'warning',
            status='failed',
            reason='invalid_credentials',
            user_id=user.id if user and not user.is_deleted else None,
            username=username or '-',
            email=user.email if user and not user.is_deleted else '-',
            nickname=user.nickname if user and not user.is_deleted else '-',
            role=user.role if user and not user.is_deleted else '-',
            remember_me=remember_me,
            ip=client_ip
        )
        return jsonify({'error': '帳號或密碼錯誤'}), 401

    if not user.email_verified:
        write_sign_in_log(
            'warning',
            status='failed',
            reason='email_unverified',
            user_id=user.id,
            username=user.username,
            email=user.email,
            nickname=user.nickname or '-',
            role=user.role,
            remember_me=remember_me,
            ip=client_ip
        )
        return jsonify({'error': '請先驗證你的 Email'}), 403  # 👈 阻止登入

    refresh_expires = timedelta(days=7 if remember_me else 1)
    token = create_access_token(identity=str(user.id), additional_claims={'role': user.role})
    refresh_token = create_refresh_token(
        identity=str(user.id),
        additional_claims={'role': user.role, 'remember_me': remember_me},
        expires_delta=refresh_expires
    )
    write_sign_in_log(
        'info',
        status='success',
        reason='authenticated',
        user_id=user.id,
        username=user.username,
        email=user.email,
        nickname=user.nickname or '-',
        role=user.role,
        remember_me=remember_me,
        refresh_expires_in_days=7 if remember_me else 1,
        ip=client_ip
    )
    return jsonify({
        'access_token': token,
        'refresh_token': refresh_token,
        'refresh_expires_in_days': 7 if remember_me else 1,
        'is_verified': True,  # 明確標示用戶已驗證
        'require_verification': False,  # 告訴前端不需要驗證
        'role': user.role,
        'username': user.username,
        'user_id': user.id,
    })


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_access_token():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user or user.is_deleted:
        return jsonify({'error': 'User not found'}), 404

    token = create_access_token(identity=str(user.id), additional_claims={'role': user.role})
    return jsonify({
        'access_token': token,
        'role': user.role,
        'username': user.username,
        'user_id': user.id,
    })
