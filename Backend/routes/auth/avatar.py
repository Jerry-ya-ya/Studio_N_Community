from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from models import db
from routes.auth.utils import get_current_user_from_token
from routes.auth.account_log import log_account_event
from image_upload import (
    ImageStorageError,
    InvalidImageError,
    delete_uploaded_image,
    upload_validated_image,
)

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

    try:
        stored_image = upload_validated_image(file, f'avatars/user-{user.id}')
    except InvalidImageError as error:
        return jsonify({'error': str(error), 'code': 'invalid_image'}), 400
    except ImageStorageError:
        return jsonify({'error': 'Image storage is temporarily unavailable', 'code': 'image_storage_unavailable'}), 503

    previous_avatar_url = user.avatar_url
    previous_avatar_source = user.avatar_source or 'github'
    user.avatar_url = stored_image.url
    user.avatar_source = 'local'
    db.session.commit()
    delete_uploaded_image(previous_avatar_url)
    log_account_event(
        'upload_avatar',
        user,
        filename=stored_image.blob_name,
        avatar_url=user.avatar_url,
        previous_avatar_url=previous_avatar_url,
        previous_avatar_source=previous_avatar_source,
        avatar_source=user.avatar_source,
    )

    return jsonify({
        'message': 'Avatar uploaded',
        'avatar_url': user.avatar_url,
        'avatar_source': user.avatar_source,
        'avatarSource': user.avatar_source,
    })
