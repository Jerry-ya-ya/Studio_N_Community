from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from models import UserSchedule, db
from routes.auth.utils import get_current_user_from_token
from time_utils import to_taipei_iso


schedule_bp = Blueprint('schedule', __name__)

MAX_COLUMNS = 5
MAX_ROWS = 8
MAX_TITLE_LENGTH = 120


def serialize_schedule(schedule):
    return {
        'blocks': schedule.blocks if schedule else [],
        'updatedAt': to_taipei_iso(schedule.updated_at) if schedule else None,
    }


def clean_schedule_blocks(raw_blocks):
    if not isinstance(raw_blocks, list):
        raise ValueError('Schedule blocks must be a list')

    cleaned_blocks = []
    occupied_slots = set()

    for raw_block in raw_blocks:
        if not isinstance(raw_block, dict):
            raise ValueError('Each schedule block must be an object')

        try:
            block_id = int(raw_block.get('id'))
            column = int(raw_block.get('column'))
            start_row = int(raw_block.get('startRow'))
            span = int(raw_block.get('span'))
        except (TypeError, ValueError):
            raise ValueError('Schedule block fields must be valid integers') from None

        title = str(raw_block.get('title', '')).strip()[:MAX_TITLE_LENGTH] or 'New class'

        if block_id <= 0:
            raise ValueError('Schedule block id must be positive')
        if column < 0 or column >= MAX_COLUMNS:
            raise ValueError('Schedule block column is out of range')
        if start_row < 1 or start_row > MAX_ROWS:
            raise ValueError('Schedule block start row is out of range')
        if span < 1 or start_row + span - 1 > MAX_ROWS:
            raise ValueError('Schedule block span is out of range')

        for row in range(start_row, start_row + span):
            slot = (column, row)
            if slot in occupied_slots:
                raise ValueError('Schedule blocks cannot overlap')
            occupied_slots.add(slot)

        cleaned_blocks.append({
            'id': block_id,
            'column': column,
            'startRow': start_row,
            'span': span,
            'title': title,
        })

    return cleaned_blocks


@schedule_bp.route('/schedule', methods=['GET'])
@jwt_required()
def get_schedule():
    user = get_current_user_from_token()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    schedule = UserSchedule.query.filter_by(user_id=user.id).first()
    return jsonify(serialize_schedule(schedule))


@schedule_bp.route('/schedule', methods=['PUT'])
@jwt_required()
def update_schedule():
    user = get_current_user_from_token()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json(silent=True) or {}

    try:
        blocks = clean_schedule_blocks(data.get('blocks', []))
    except ValueError as error:
        return jsonify({'error': str(error)}), 400

    schedule = UserSchedule.query.filter_by(user_id=user.id).first()
    if not schedule:
        schedule = UserSchedule(user_id=user.id, blocks=blocks)
        db.session.add(schedule)
    else:
        schedule.blocks = blocks

    db.session.commit()
    return jsonify(serialize_schedule(schedule))
