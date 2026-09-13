from functools import wraps
from flask_jwt_extended import verify_jwt_in_request
from flask import g, jsonify
from routes.auth.utils import get_current_user_from_token
from role_groups import Permission, has_permission

def permission_required(permission, error_message):
    """Build a route decorator backed by the central role-group registry."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user = get_current_user_from_token()
            if not user:
                return jsonify({'error': '使用者不存在'}), 401
            if not has_permission(user.role, permission):
                return jsonify({'error': error_message}), 403
            g.current_user = user
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def admin_required(fn):
    return permission_required(Permission.ADMIN_ACCESS, '需要管理員權限')(fn)

def superadmin_required(fn):
    return permission_required(Permission.MANAGE_ROLES, '需要最高管理員權限')(fn)
