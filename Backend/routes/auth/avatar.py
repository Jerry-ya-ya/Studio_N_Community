import os

from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename
from models import db
from routes.auth.utils import get_current_user_from_token

avatar_bp = Blueprint('avatar', __name__)

@avatar_bp.route('/avatar', methods=['POST'])
@jwt_required()
def upload_avatar():
    user = get_current_user_from_token()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # 設定上傳檔案的類型
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    # 檢查副檔名
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        # 確保上傳目錄存在
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'avatar')
        os.makedirs(upload_folder, exist_ok=True)
        
        filename = secure_filename(f"{user.username}_{file.filename}")
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)

        # 使用正斜線作為 URL 路徑
        user.avatar_url = f'/static/uploads/avatar/{filename}'
        user.avatar_source = 'local'
        db.session.commit()

        return jsonify({
            'message': 'Avatar uploaded',
            'avatar_url': user.avatar_url,
            'avatar_source': user.avatar_source,
            'avatarSource': user.avatar_source,
        })

    return jsonify({'error': 'Invalid file type'}), 400
