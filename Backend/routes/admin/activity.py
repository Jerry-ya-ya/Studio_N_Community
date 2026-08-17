import os
import uuid

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename

from models import ActivityPromotion, db
from routes.admin.decorators import admin_required
from routes.auth.utils import get_current_user_from_token
from time_utils import to_taipei_iso

activity_bp = Blueprint('activity', __name__)

VALID_VISIBILITIES = {'public', 'private'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def is_allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def serialize_activity(activity):
    creator = activity.created_by

    return {
        'id': activity.id,
        'title': activity.title,
        'description': activity.description,
        'visibility': activity.visibility,
        'targetFilter': activity.target_filter,
        'target_filter': activity.target_filter,
        'imageUrl': activity.image_url,
        'image_url': activity.image_url,
        'sort_order': activity.sort_order,
        'createdBy': creator.display_username if creator else None,
        'created_by_id': activity.created_by_id,
        'created_at': to_taipei_iso(activity.created_at),
        'updated_at': to_taipei_iso(activity.updated_at),
    }


def matches_activity_target(activity, user):
    target_filter = (activity.target_filter or 'all').strip().lower()
    if target_filter in {'', 'all', '*'}:
        return True

    role = (user.role or '').lower()
    username = (user.username or '').lower()

    if target_filter.startswith('role:'):
        return target_filter.split(':', 1)[1].strip() == role
    if target_filter.startswith('user:'):
        return target_filter.split(':', 1)[1].strip().lower() == username

    return target_filter in {role, username}


def read_activity_payload(data, default_order=0):
    if not isinstance(data, dict):
        return None, ('activity must be an object', 400)

    title = (data.get('title') or '').strip()
    description = (data.get('description') or '').strip()
    visibility = (data.get('visibility') or 'private').strip()
    target_filter = (data.get('targetFilter') or data.get('target_filter') or 'all').strip()
    image_url = (data.get('imageUrl') or data.get('image_url') or '').strip()
    sort_order = data.get('sort_order', default_order)

    if not title:
        return None, ('title is required', 400)
    if not description:
        return None, ('description is required', 400)
    if visibility not in VALID_VISIBILITIES:
        return None, ('visibility must be public or private', 400)

    try:
        sort_order = int(sort_order)
    except (TypeError, ValueError):
        return None, ('sort_order must be a number', 400)

    return {
        'title': title[:120],
        'description': description,
        'visibility': visibility,
        'target_filter': (target_filter or 'all')[:160],
        'image_url': image_url[:255] or None,
        'sort_order': sort_order,
    }, None


@activity_bp.route('/activities', methods=['GET'])
def public_activities():
    activities = ActivityPromotion.query.filter_by(visibility='public').order_by(
        ActivityPromotion.sort_order.asc(),
        ActivityPromotion.created_at.desc(),
        ActivityPromotion.id.desc()
    ).all()

    return jsonify([serialize_activity(activity) for activity in activities])


@activity_bp.route('/private/activities', methods=['GET'])
@jwt_required()
def private_activities():
    user = get_current_user_from_token()
    if not user:
        return jsonify({'error': '使用者不存在'}), 401

    activities = ActivityPromotion.query.filter_by(visibility='private').order_by(
        ActivityPromotion.sort_order.asc(),
        ActivityPromotion.created_at.desc(),
        ActivityPromotion.id.desc()
    ).all()

    visible_activities = [
        activity for activity in activities
        if matches_activity_target(activity, user)
    ]

    return jsonify([serialize_activity(activity) for activity in visible_activities])


@activity_bp.route('/admin/activities', methods=['GET'])
@admin_required
def admin_activities():
    activities = ActivityPromotion.query.order_by(
        ActivityPromotion.sort_order.asc(),
        ActivityPromotion.created_at.desc(),
        ActivityPromotion.id.desc()
    ).all()

    return jsonify([serialize_activity(activity) for activity in activities])


@activity_bp.route('/admin/activities', methods=['POST'])
@admin_required
def create_activity():
    data = request.get_json(silent=True) or {}
    payload, error = read_activity_payload(data)
    if error:
        message, status = error
        return jsonify({'error': message}), status

    user = get_current_user_from_token()
    activity = ActivityPromotion(**payload, created_by_id=user.id if user else None)
    db.session.add(activity)
    db.session.commit()

    return jsonify(serialize_activity(activity)), 201


@activity_bp.route('/admin/activities/<int:activity_id>', methods=['PUT'])
@admin_required
def update_activity(activity_id):
    activity = ActivityPromotion.query.get_or_404(activity_id)
    data = request.get_json(silent=True) or {}
    payload, error = read_activity_payload(data, default_order=activity.sort_order)
    if error:
        message, status = error
        return jsonify({'error': message}), status

    for key, value in payload.items():
        setattr(activity, key, value)
    db.session.commit()

    return jsonify(serialize_activity(activity))


@activity_bp.route('/admin/activities/<int:activity_id>/image', methods=['POST'])
@admin_required
def upload_activity_image(activity_id):
    activity = ActivityPromotion.query.get_or_404(activity_id)
    uploaded_file = request.files.get('file') or request.files.get('image') or request.files.get('background')

    if not uploaded_file:
        return jsonify({'error': 'No file part'}), 400
    if uploaded_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not is_allowed_image(uploaded_file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'activity')
    os.makedirs(upload_folder, exist_ok=True)

    original_name = secure_filename(uploaded_file.filename)
    extension = original_name.rsplit('.', 1)[1].lower()
    filename = f'{activity.id}_{uuid.uuid4().hex}.{extension}'
    filepath = os.path.join(upload_folder, filename)
    uploaded_file.save(filepath)

    activity.image_url = f'/static/uploads/activity/{filename}'
    db.session.commit()

    return jsonify(serialize_activity(activity))


@activity_bp.route('/admin/activities/<int:activity_id>/image', methods=['DELETE'])
@admin_required
def clear_activity_image(activity_id):
    activity = ActivityPromotion.query.get_or_404(activity_id)
    activity.image_url = None
    db.session.commit()

    return jsonify(serialize_activity(activity))


@activity_bp.route('/admin/activities/<int:activity_id>', methods=['DELETE'])
@admin_required
def delete_activity(activity_id):
    activity = ActivityPromotion.query.get_or_404(activity_id)
    db.session.delete(activity)
    db.session.commit()

    return jsonify({'message': 'activity deleted', 'id': activity_id})
