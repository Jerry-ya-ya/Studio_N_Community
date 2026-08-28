import os

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from models import db
from routes.auth.utils import get_current_user_from_token
from image_upload import InvalidImageError, save_validated_image

avatar_bp = Blueprint('avatar', __name__)

@avatar_bp.route('/avatar', methods=['POST'])
@jwt_required()
def upload_avatar():
    user = get_current_user_from_token()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'avatar')
    try:
        filename = save_validated_image(file, upload_folder, f'user-{user.id}')
    except InvalidImageError as error:
        return jsonify({'error': str(error), 'code': 'invalid_image'}), 400

    user.avatar_url = f'/static/uploads/avatar/{filename}'
    user.avatar_source = 'local'
    db.session.commit()

    return jsonify({
        'message': 'Avatar uploaded',
        'avatar_url': user.avatar_url,
        'avatar_source': user.avatar_source,
        'avatarSource': user.avatar_source,
    })
