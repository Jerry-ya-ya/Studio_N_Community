import json

from flask import Blueprint, jsonify, request

from log_writer import get_backend_logger
from models import DailyCheckIn, User
from models import db
from role_groups import (
    Role,
    assignable_role_names,
    get_role_group,
    serialized_role_groups,
)
from routes.admin.decorators import superadmin_required
from routes.auth.utils import get_current_user_from_token
from time_utils import taipei_now, to_taipei_iso

promote_bp = Blueprint('promote', __name__)
admin_role_logger = get_backend_logger('admin_role', 'admin_role.log', message_only=True)


def get_client_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()


def log_admin_role_change(action, acting_user, target_user, previous_role, new_role):
    payload = {
        'event': 'admin_role',
        'action': action,
        'status': 'success',
        'logged_at': to_taipei_iso(taipei_now()),
        'admin_id': acting_user.id,
        'superadmin_id': acting_user.id,
        'username': acting_user.display_username,
        'nickname': acting_user.display_nickname or '-',
        'role': acting_user.role,
        'ip': get_client_ip(),
        'target_user_id': target_user.id,
        'target_username': target_user.display_username,
        'target_nickname': target_user.display_nickname or '-',
        'previous_role': previous_role,
        'new_role': new_role,
    }
    admin_role_logger.info(json.dumps(payload, ensure_ascii=False))


def change_user_role(user, acting_user, new_role, action='set_user_role'):
    """Apply one validated account role change for every role-management route."""
    new_group = get_role_group(new_role)
    if not new_group:
        return None, (
            jsonify({
                'error': '無效的身分群組',
                'allowed_roles': assignable_role_names(),
            }),
            400,
        )

    if user.role == new_role:
        return False, None

    if user.id == acting_user.id:
        return None, (jsonify({'error': '不能變更自己的身分群組'}), 400)

    current_group = get_role_group(user.role)
    if not new_group.assignable or (current_group and not current_group.assignable):
        return None, (jsonify({'error': '最高管理員身分不可透過此介面變更'}), 400)

    previous_role = user.role
    user.role = new_role
    db.session.commit()
    log_admin_role_change(action, acting_user, user, previous_role, new_role)
    return True, None

@promote_bp.route('/superadmin/promote', methods=['GET'])
@superadmin_required
def get_users():
    # 讀 query string
    sort_by = request.args.get('sort_by', 'id')
    order = request.args.get('order', 'asc')

    sort_columns = {
        'id': User.id,
        'created_at': User.created_at,
        'username': User.username,
        'role': User.role,
    }
    sort_column = sort_columns.get(sort_by, User.id)

    # 排序方向
    if order == 'desc':
        users = User.query.order_by(sort_column.desc()).all()
    else:
        users = User.query.order_by(sort_column.asc()).all()

    point_rows = db.session.query(
        DailyCheckIn.user_id,
        db.func.coalesce(db.func.sum(DailyCheckIn.points), 0).label('total_points')
    ).group_by(DailyCheckIn.user_id).all()
    point_map = {user_id: int(total_points or 0) for user_id, total_points in point_rows}

    result = []
    for user in users:
        user_data = user.to_dict(include_sensitive=True)
        total_points = point_map.get(user.id, 0)
        user_data['total_points'] = total_points
        user_data['totalPoints'] = total_points
        user_data['coins'] = total_points
        user_data['total_coins'] = total_points
        user_data['totalCoins'] = total_points
        user_data['experience'] = user.experience or 0
        result.append(user_data)

    return jsonify(result)


@promote_bp.route('/superadmin/role-groups', methods=['GET'])
@superadmin_required
def get_role_groups():
    """Expose the same registry used by backend authorization to management UIs."""
    return jsonify(serialized_role_groups())


@promote_bp.route('/superadmin/users/<int:user_id>/role', methods=['PUT'])
@superadmin_required
def update_user_role(user_id):
    acting_user = get_current_user_from_token()
    if not acting_user:
        return jsonify({'error': '使用者不存在'}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': '用戶不存在'}), 404

    data = request.get_json(silent=True) or {}
    new_role = data.get('role')
    if not isinstance(new_role, str) or not new_role.strip():
        return jsonify({
            'error': '請提供身分群組',
            'allowed_roles': assignable_role_names(),
        }), 400
    new_role = new_role.strip().lower()

    changed, error_response = change_user_role(user, acting_user, new_role)
    if error_response:
        return error_response

    return jsonify({
        'message': f'{user.username} 的身分群組已設為 {new_role}' if changed else '身分群組未變更',
        'user': user.to_dict(),
    })

@promote_bp.route('/superadmin/promote/<int:user_id>', methods=['PUT'])
@superadmin_required
def promote_user(user_id):
    acting_user = get_current_user_from_token()
    if not acting_user:
        return jsonify({'error': '使用者不存在'}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': '用戶不存在'}), 404

    if user.role == Role.ADMIN.value:
        return jsonify({'message': '該用戶已是管理員'}), 200

    _, error_response = change_user_role(
        user,
        acting_user,
        Role.ADMIN.value,
        action='promote_user',
    )
    if error_response:
        return error_response

    return jsonify({'message': f'已將 {user.username} 晉升為管理員'})

@promote_bp.route('/superadmin/demote/<int:user_id>', methods=['PUT'])
@superadmin_required
def demote_user(user_id):
    acting_user = get_current_user_from_token()
    if not acting_user:
        return jsonify({'error': '使用者不存在'}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': '用戶不存在'}), 404

    if user.id == acting_user.id:
        return jsonify({'error': '不能降級自己'}), 400

    if user.role != Role.ADMIN.value:
        return jsonify({'message': '該用戶不是管理員'}), 200

    _, error_response = change_user_role(
        user,
        acting_user,
        Role.USER.value,
        action='demote_user',
    )
    if error_response:
        return error_response

    return jsonify({'message': f'{user.username} 已降級為一般使用者'})
