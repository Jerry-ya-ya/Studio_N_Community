from flask import Blueprint, jsonify, request
from models import User
from flask_jwt_extended import jwt_required
from time_utils import to_taipei_iso
from profile_stats import get_coin_balances, serialize_profile_stats

square_bp = Blueprint('square', __name__)

@square_bp.route('/square', methods=['GET'])
@jwt_required()
def get_square():
    # 從 query string 讀排序條件，預設 id ASC
    sort_by = request.args.get('sort_by', 'id')
    order = request.args.get('order', 'asc')

    sort_columns = {
        'id': User.id,
        'created_at': User.created_at,
        'username': User.username,
        'role': User.role,
    }
    sort_column = sort_columns.get(sort_by, User.id)

    # 決定升冪還是降冪
    if order == 'desc':
        users = User.query.order_by(sort_column.desc()).all()
    else:
        users = User.query.order_by(sort_column.asc()).all()

    coin_balances = get_coin_balances(users)
    user_list = [{
        'id': user.id,
        'username': user.display_username,
        'nickname': user.display_nickname,
        'avatar_url': user.avatar_url,
        'role': user.role,
        'created_at': to_taipei_iso(user.created_at),
        **serialize_profile_stats(user, coin_balances.get(user.id, 0)),
    } for user in users]

    return jsonify(user_list)
