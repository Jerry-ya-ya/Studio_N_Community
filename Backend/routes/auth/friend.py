from flask_jwt_extended import jwt_required
from models import db, User, FriendRequest
from flask import request, jsonify, Blueprint
from routes.auth.utils import get_current_user_from_token

friend_bp = Blueprint('friend_bp', __name__)

# @friend_bp.route('/friends/follow', methods=['POST'])
# @jwt_required()
# def add_friend():
#     identity = get_jwt_identity()
#     current_user = User.query.filter_by(username=identity).first()

#     data = request.get_json()
#     friend_username = data.get('friend_username')
#     friend = User.query.filter_by(username=friend_username).first()

#     if not friend:
#         return jsonify({'error': '該用戶不存在'}), 404
#     if friend == current_user:
#         return jsonify({'error': '不能加自己為好友'}), 400
#     if friend in current_user.friends:
#         return jsonify({'message': '已是好友'}), 200

#     current_user.friends.append(friend)
#     db.session.commit()
#     return jsonify({'message': f'已加 {friend.username} 為好友'})

@friend_bp.route('/friends/remove/<int:friend_id>', methods=['DELETE'])
@jwt_required()
def remove_friend(friend_id):
    current_user = get_current_user_from_token()
    if not current_user:
        return jsonify({'error': 'User not found'}), 404
    friend = User.query.get(friend_id)

    if not friend:
        return jsonify({'error': '找不到用戶'}), 404
    if friend not in current_user.friends:
        return jsonify({'error': '此用戶不是你的好友'}), 400

    current_user.friends.remove(friend)
    db.session.commit()

    return jsonify({'message': f'已刪除 {friend.username} 為好友'})

@friend_bp.route('/friends/list', methods=['GET'])
@jwt_required()
def get_friends():
    user = get_current_user_from_token()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify([
        {
            'id': f.id,
            'username': f.username,
            'name': f.nickname or f.username,
            'nickname': f.nickname,
            'email': f.email,
            'githubUrl': f.github_url or '',
            'avatarUrl': f.avatar_url,
            'avatarSource': f.avatar_source or 'github',
            'role': f.role,
        }
        for f in user.friends
    ])

@friend_bp.route('/friends/request', methods=['POST'])
@jwt_required()
def send_friend_request():
    current_user = get_current_user_from_token()
    if not current_user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json(silent=True) or {}
    to_username = data.get('to_username')
    if not to_username:
        return jsonify({'error': '請填寫使用者名稱'}), 400
    to_user = User.query.filter_by(username=to_username).first()

    if not to_user or to_user == current_user:
        return jsonify({'error': '用戶不存在或無效'}), 400

    if to_user in current_user.friends:
        return jsonify({'message': '你們已是好友'}), 200

    existing_request = FriendRequest.query.filter_by(
        from_user_id=current_user.id,
        to_user_id=to_user.id
    ).first()
    if existing_request:
        return jsonify({'message': '已發送邀請'}), 200

    new_request = FriendRequest(from_user_id=current_user.id, to_user_id=to_user.id)
    db.session.add(new_request)
    db.session.commit()

    return jsonify({'message': '邀請已發送'})

@friend_bp.route('/friends/requests', methods=['GET'])
@jwt_required()
def get_friend_requests():
    current_user = get_current_user_from_token()
    if not current_user:
        return jsonify({'error': 'User not found'}), 404

    requests = FriendRequest.query.filter_by(to_user_id=current_user.id).all()
    return jsonify([
        {'id': r.id, 'from_username': r.from_user.username}
        for r in requests
    ])

@friend_bp.route('/friends/accept/<int:request_id>', methods=['POST'])
@jwt_required()
def accept_friend_request(request_id):
    current_user = get_current_user_from_token()
    if not current_user:
        return jsonify({'error': 'User not found'}), 404

    req = FriendRequest.query.get(request_id)
    if not req or req.to_user_id != current_user.id:
        return jsonify({'error': '邀請不存在'}), 404

    from_user = req.from_user
    if from_user not in current_user.friends:
        current_user.friends.append(from_user)
    if current_user not in from_user.friends:
        from_user.friends.append(current_user)

    db.session.delete(req)
    db.session.commit()

    return jsonify({'message': f'你與 {from_user.username} 已成為好友'})

@friend_bp.route('/friends/reject/<int:request_id>', methods=['POST'])
@jwt_required()
def reject_friend_request(request_id):
    current_user = get_current_user_from_token()
    if not current_user:
        return jsonify({'error': 'User not found'}), 404

    req = FriendRequest.query.get(request_id)
    if not req or req.to_user_id != current_user.id:
        return jsonify({'error': '邀請不存在'}), 404

    db.session.delete(req)
    db.session.commit()
    return jsonify({'message': '已拒絕好友邀請'})
