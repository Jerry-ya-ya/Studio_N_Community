from flask import Blueprint, request, jsonify, abort
from flask_jwt_extended import jwt_required
from models import db, Post, PostLike
from routes.auth.utils import get_current_user_from_token
from time_utils import to_taipei_text

post_bp = Blueprint('post', __name__)

def get_pagination_args(default_per_page=20, max_per_page=50):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', default_per_page, type=int)

    page = max(page or 1, 1)
    per_page = min(max(per_page or default_per_page, 1), max_per_page)
    return page, per_page

def serialize_post(post, include_user=False, current_user_id=None):
    data = {
        'id': post.id,
        'content': post.content,
        'created_at': to_taipei_text(post.created_at),
        'user_id': post.user_id,
        'like_count': len(post.likes),
        'liked_by_me': any(like.user_id == current_user_id for like in post.likes) if current_user_id else False,
    }

    if include_user:
        data['user'] = {
            'id': post.user.id,
            'username': post.user.display_username,
            'nickname': post.user.display_nickname,
            'avatar_url': post.user.avatar_url,
            'role': post.user.role
        }

    return data

@post_bp.route('/post', methods=['POST'])
@jwt_required()
def create_post():
    user = get_current_user_from_token()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json(silent=True) or {}
    content = data.get('content', '').strip()

    if not content:
        return jsonify({'error': '內容不能為空'}), 400

    post = Post(content=content, user_id=user.id)
    db.session.add(post)
    db.session.commit()

    return jsonify({'message': '貼文已新增'})

@post_bp.route('/post', methods=['GET'])
@jwt_required()
def get_all_posts():
    user = get_current_user_from_token()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    page, per_page = get_pagination_args()
    posts = (
        Post.query
        .order_by(Post.created_at.desc())
        .limit(per_page)
        .offset((page - 1) * per_page)
        .all()
    )

    return jsonify([serialize_post(post, include_user=True, current_user_id=user.id) for post in posts])

@post_bp.route('/post/me', methods=['GET'])
@jwt_required()
def get_my_posts():
    user = get_current_user_from_token()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    page, per_page = get_pagination_args()
    posts = (
        Post.query
        .filter_by(user_id=user.id)
        .order_by(Post.created_at.desc())
        .limit(per_page)
        .offset((page - 1) * per_page)
        .all()
    )

    return jsonify([serialize_post(post, current_user_id=user.id) for post in posts])

@post_bp.route('/post/<int:post_id>/like', methods=['POST'])
@jwt_required()
def toggle_post_like(post_id):
    user = get_current_user_from_token()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    post = Post.query.get_or_404(post_id)
    like = PostLike.query.filter_by(post_id=post.id, user_id=user.id).first()

    if like:
        db.session.delete(like)
        liked = False
    else:
        db.session.add(PostLike(post_id=post.id, user_id=user.id))
        liked = True

    db.session.commit()

    return jsonify({
        'liked_by_me': liked,
        'like_count': PostLike.query.filter_by(post_id=post.id).count()
    })

# 修改貼文
@post_bp.route('/post/<int:post_id>', methods=['PUT'])
@jwt_required()
def update_post(post_id):
    user = get_current_user_from_token()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    post = Post.query.get_or_404(post_id)
    if post.user_id != user.id:
        abort(403, description='無權限修改此貼文')

    data = request.get_json(silent=True) or {}
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'error': '內容不能為空'}), 400

    post.content = content
    db.session.commit()
    return jsonify({'message': '已更新'})

# 刪除貼文
@post_bp.route('/post/<int:post_id>', methods=['DELETE'])
@jwt_required()
def delete_post(post_id):
    user = get_current_user_from_token()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    post = Post.query.get_or_404(post_id)
    if post.user_id != user.id:
        abort(403, description='無權限刪除此貼文')

    db.session.delete(post)
    db.session.commit()
    return jsonify({'message': '已刪除'})
