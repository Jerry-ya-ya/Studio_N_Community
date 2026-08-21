from flask import Blueprint, jsonify, request
from models import DailyCheckIn, User
from models import db
from routes.admin.decorators import superadmin_required
from routes.auth.utils import get_current_user_from_token

promote_bp = Blueprint('promote', __name__)

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
        user_data = user.to_dict()
        total_points = point_map.get(user.id, 0)
        user_data['total_points'] = total_points
        user_data['totalPoints'] = total_points
        user_data['coins'] = total_points
        user_data['total_coins'] = total_points
        user_data['totalCoins'] = total_points
        user_data['experience'] = user.experience or 0
        result.append(user_data)

    return jsonify(result)

@promote_bp.route('/superadmin/promote/<int:user_id>', methods=['PUT'])
@superadmin_required
def promote_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用戶不存在'}), 404

    if user.role == 'admin':
        return jsonify({'message': '該用戶已是管理員'}), 200

    user.role = 'admin'
    db.session.commit()

    return jsonify({'message': f'已將 {user.username} 晉升為管理員'})

@promote_bp.route('/superadmin/demote/<int:user_id>', methods=['PUT'])
@superadmin_required
def demote_user(user_id):
    acting_user = get_current_user_from_token()
    if not acting_user:
        return jsonify({'error': '使用者不存在'}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用戶不存在'}), 404

    if user.id == acting_user.id:
        return jsonify({'error': '不能降級自己'}), 400

    if user.role != 'admin':
        return jsonify({'message': '該用戶不是管理員'}), 200

    user.role = 'user'
    db.session.commit()
    return jsonify({'message': f'{user.username} 已降級為一般使用者'})
