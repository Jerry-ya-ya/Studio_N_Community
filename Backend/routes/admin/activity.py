import os
import json
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required

from models import ActivityPromotion, db
from routes.admin.decorators import admin_required
from routes.auth.utils import get_current_user_from_token
from time_utils import taipei_now, to_taipei_iso
from image_upload import InvalidImageError, save_validated_image
from log_writer import get_backend_logger
from role_groups import Permission, has_permission

activity_bp = Blueprint('activity', __name__)
activity_logger = get_backend_logger('activity', 'activity.log', message_only=True)

VALID_VISIBILITIES = {'public', 'private'}


def get_client_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()


def log_activity_event(action, activity=None, **payload):
    user = get_current_user_from_token()
    activity_id = payload.pop('activity_id', None)
    title = payload.pop('title', None)
    visibility = payload.pop('visibility', None)
    log_payload = {
        'event': 'admin_activity',
        'action': action,
        'status': 'success',
        'logged_at': to_taipei_iso(taipei_now()),
        'admin_id': user.id if user else None,
        'username': user.display_username if user else 'Admin',
        'nickname': (user.display_nickname or '-') if user else '-',
        'role': user.role if user else '-',
        'ip': get_client_ip(),
        'activity_id': activity_id if activity_id is not None else activity.id,
        'title': title if title is not None else activity.title,
        'visibility': visibility if visibility is not None else activity.visibility,
        **payload,
    }
    activity_logger.info(json.dumps(log_payload, ensure_ascii=False))


def serialize_activity(activity):
    creator = activity.created_by
    is_ended = bool(activity.end_at and activity.end_at <= taipei_now())

    return {
        'id': activity.id,
        'title': activity.title,
        'description': activity.description,
        'visibility': activity.visibility,
        'targetFilter': activity.target_filter,
        'target_filter': activity.target_filter,
        'imageUrl': activity.image_url,
        'image_url': activity.image_url,
        'startAt': to_taipei_iso(activity.start_at),
        'start_at': to_taipei_iso(activity.start_at),
        'endAt': to_taipei_iso(activity.end_at),
        'end_at': to_taipei_iso(activity.end_at),
        'status': 'ended' if is_ended else 'active',
        'isEnded': is_ended,
        'is_ended': is_ended,
        'sort_order': activity.sort_order,
        'createdBy': creator.display_username if creator else None,
        'created_by_id': activity.created_by_id,
        'created_at': to_taipei_iso(activity.created_at),
        'updated_at': to_taipei_iso(activity.updated_at),
    }


def matches_activity_target(activity, user):
    target_filter = (activity.target_filter or 'all').strip().lower()
    role = (user.role or '').lower()

    if has_permission(role, Permission.ADMIN_ACCESS):
        return True

    if target_filter in {'', 'all', '*'}:
        return True

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
    start_at, start_error = read_activity_datetime(data.get('startAt') or data.get('start_at'))
    end_at, end_error = read_activity_datetime(data.get('endAt') or data.get('end_at'))
    sort_order = data.get('sort_order', default_order)

    if not title:
        return None, ('title is required', 400)
    if not description:
        return None, ('description is required', 400)
    if visibility not in VALID_VISIBILITIES:
        return None, ('visibility must be public or private', 400)
    if start_error:
        return None, ('startAt must be an ISO datetime', 400)
    if end_error:
        return None, ('endAt must be an ISO datetime', 400)
    if start_at and end_at and end_at < start_at:
        return None, ('endAt must be after startAt', 400)

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
        'start_at': start_at,
        'end_at': end_at,
        'sort_order': sort_order,
    }, None


def read_activity_datetime(value):
    if not value:
        return None, None

    if not isinstance(value, str):
        return None, True

    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None, True

    return parsed.replace(tzinfo=None), None


@activity_bp.route('/activities', methods=['GET'])
def public_activities():
    activities = ActivityPromotion.query.filter_by(visibility='public').order_by(
        ActivityPromotion.sort_order.asc(),
        ActivityPromotion.created_at.desc(),
        ActivityPromotion.id.desc()
    ).all()

    response = jsonify([serialize_activity(activity) for activity in activities])
    response.headers['Cache-Control'] = 'no-store'
    return response


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

    response = jsonify([serialize_activity(activity) for activity in visible_activities])
    response.headers['Cache-Control'] = 'no-store'
    return response


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
    log_activity_event('create_activity', activity)

    return jsonify(serialize_activity(activity)), 201


@activity_bp.route('/admin/activities/<int:activity_id>', methods=['PUT'])
@admin_required
def update_activity(activity_id):
    activity = ActivityPromotion.query.get_or_404(activity_id)
    previous_values = {
        key: to_taipei_iso(value) if isinstance(value, datetime) else value
        for key, value in {
            'title': activity.title,
            'description': activity.description,
            'visibility': activity.visibility,
            'target_filter': activity.target_filter,
            'image_url': activity.image_url,
            'start_at': activity.start_at,
            'end_at': activity.end_at,
            'sort_order': activity.sort_order,
        }.items()
    }
    data = request.get_json(silent=True) or {}
    payload, error = read_activity_payload(data, default_order=activity.sort_order)
    if error:
        message, status = error
        return jsonify({'error': message}), status

    for key, value in payload.items():
        setattr(activity, key, value)
    db.session.commit()
    changes = {
        key: {
            'from': previous_values[key],
            'to': to_taipei_iso(value) if isinstance(value, datetime) else value,
        }
        for key, value in payload.items()
        if previous_values[key] != (to_taipei_iso(value) if isinstance(value, datetime) else value)
    }
    log_activity_event('update_activity', activity, changes=changes)

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
    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'activity')
    try:
        filename = save_validated_image(uploaded_file, upload_folder, f'activity-{activity.id}')
    except InvalidImageError as error:
        return jsonify({'error': str(error), 'code': 'invalid_image'}), 400

    activity.image_url = f'/static/uploads/activity/{filename}'
    db.session.commit()
    log_activity_event(
        'upload_activity_image',
        activity,
        filename=filename,
        image_url=activity.image_url,
    )

    return jsonify(serialize_activity(activity))


@activity_bp.route('/admin/activities/<int:activity_id>/image', methods=['DELETE'])
@admin_required
def clear_activity_image(activity_id):
    activity = ActivityPromotion.query.get_or_404(activity_id)
    previous_image_url = activity.image_url
    activity.image_url = None
    db.session.commit()
    log_activity_event('clear_activity_image', activity, previous_image_url=previous_image_url)

    return jsonify(serialize_activity(activity))


@activity_bp.route('/admin/activities/<int:activity_id>', methods=['DELETE'])
@admin_required
def delete_activity(activity_id):
    activity = ActivityPromotion.query.get_or_404(activity_id)
    activity_log_data = {
        'id': activity.id,
        'title': activity.title,
        'visibility': activity.visibility,
    }
    db.session.delete(activity)
    db.session.commit()
    log_activity_event(
        'delete_activity',
        activity_id=activity_log_data['id'],
        title=activity_log_data['title'],
        visibility=activity_log_data['visibility'],
    )

    return jsonify({'message': 'activity deleted', 'id': activity_id})
