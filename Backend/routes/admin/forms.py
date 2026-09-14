from datetime import datetime
import re
from uuid import uuid4

from flask import Blueprint, g, jsonify, request

from models import FormTemplate, db
from rate_limit import authenticated_user_rate_limit_key, limiter
from routes.admin.decorators import admin_required
from time_utils import TAIPEI_TZ, taipei_now, to_taipei_iso


forms_bp = Blueprint('admin_forms', __name__)

MAX_PAYLOAD_BYTES = 128 * 1024
MAX_QUESTIONS = 100
MAX_OPTIONS = 50
FORM_FIELDS = {'title', 'description', 'schema', 'settlementAt'}
SCHEMA_FIELDS = {'schemaVersion', 'questions'}
QUESTION_FIELDS = {'id', 'type', 'title', 'description', 'required', 'options'}
OPTION_FIELDS = {'id', 'label'}
QUESTION_TYPES = {
    'short_text',
    'long_text',
    'single_choice',
    'multiple_choice',
    'dropdown',
    'number',
    'date',
    'boolean',
}
CHOICE_TYPES = {'single_choice', 'multiple_choice', 'dropdown'}
SAFE_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{1,64}$')


def validation_error(message, field=None, status=400, code='invalid_form'):
    body = {'error': message, 'code': code}
    if field:
        body['field'] = field
    return body, status


def read_limited_json():
    if request.content_length is not None and request.content_length > MAX_PAYLOAD_BYTES:
        return None, validation_error(
            'form payload is too large', status=413, code='payload_too_large'
        )
    if not request.is_json:
        return None, validation_error(
            'Content-Type must be application/json', status=415, code='unsupported_media_type'
        )

    raw_body = request.get_data(cache=True)
    if len(raw_body) > MAX_PAYLOAD_BYTES:
        return None, validation_error(
            'form payload is too large', status=413, code='payload_too_large'
        )

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, validation_error('form must be an object')
    return data, None


def read_string(value, field, *, required=False, max_length=200):
    if value is None:
        value = ''
    if not isinstance(value, str):
        return None, validation_error(f'{field} must be a string', field)

    value = value.strip()
    if required and not value:
        return None, validation_error(f'{field} is required', field)
    if len(value) > max_length:
        return None, validation_error(
            f'{field} must be at most {max_length} characters', field
        )
    if any(ord(character) < 32 and character not in '\n\r\t' for character in value):
        return None, validation_error(f'{field} contains invalid characters', field)
    return value, None


def read_identifier(value, field, prefix):
    if value in (None, ''):
        return f'{prefix}_{uuid4().hex}', None
    if not isinstance(value, str) or not SAFE_ID_PATTERN.fullmatch(value):
        return None, validation_error(
            f'{field} must contain only letters, numbers, underscores, or hyphens', field
        )
    return value, None


def read_settlement_at(value):
    """Parse an ISO-8601 cutoff, treating offset-less values as Taipei wall time."""
    if value in (None, ''):
        return None, None
    if not isinstance(value, str):
        return None, validation_error(
            'settlementAt must be an ISO-8601 datetime or null', 'settlementAt'
        )
    if 'T' not in value and ' ' not in value:
        return None, validation_error(
            'settlementAt must be an ISO-8601 datetime or null', 'settlementAt'
        )
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None, validation_error(
            'settlementAt must be an ISO-8601 datetime or null', 'settlementAt'
        )
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(TAIPEI_TZ).replace(tzinfo=None)
    return parsed, None


def normalize_option(option, question_index, option_index):
    path = f'schema.questions[{question_index}].options[{option_index}]'
    if not isinstance(option, dict):
        return None, validation_error(f'{path} must be an object', path)
    unknown = set(option) - OPTION_FIELDS
    if unknown:
        return None, validation_error(
            f'{path} contains unsupported fields: {", ".join(sorted(unknown))}', path
        )

    option_id, error = read_identifier(option.get('id'), f'{path}.id', 'o')
    if error:
        return None, error
    label, error = read_string(
        option.get('label'), f'{path}.label', required=True, max_length=200
    )
    if error:
        return None, error
    return {'id': option_id, 'label': label}, None


def normalize_question(question, index):
    path = f'schema.questions[{index}]'
    if not isinstance(question, dict):
        return None, validation_error(f'{path} must be an object', path)
    unknown = set(question) - QUESTION_FIELDS
    if unknown:
        return None, validation_error(
            f'{path} contains unsupported fields: {", ".join(sorted(unknown))}', path
        )

    question_id, error = read_identifier(question.get('id'), f'{path}.id', 'q')
    if error:
        return None, error
    question_type = question.get('type')
    if question_type not in QUESTION_TYPES:
        return None, validation_error(
            f'{path}.type is not supported', f'{path}.type'
        )
    title, error = read_string(
        question.get('title'), f'{path}.title', required=True, max_length=300
    )
    if error:
        return None, error
    description, error = read_string(
        question.get('description'), f'{path}.description', max_length=500
    )
    if error:
        return None, error
    required = question.get('required', False)
    if not isinstance(required, bool):
        return None, validation_error(
            f'{path}.required must be a boolean', f'{path}.required'
        )

    raw_options = question.get('options', [])
    if not isinstance(raw_options, list):
        return None, validation_error(
            f'{path}.options must be a list', f'{path}.options'
        )
    if len(raw_options) > MAX_OPTIONS:
        return None, validation_error(
            f'{path}.options cannot contain more than {MAX_OPTIONS} items',
            f'{path}.options',
        )
    if question_type in CHOICE_TYPES and len(raw_options) < 2:
        return None, validation_error(
            f'{path}.options must contain at least 2 items', f'{path}.options'
        )
    if question_type not in CHOICE_TYPES and raw_options:
        return None, validation_error(
            f'{path}.options are only allowed for choice questions', f'{path}.options'
        )

    options = []
    option_ids = set()
    for option_index, option in enumerate(raw_options):
        normalized, error = normalize_option(option, index, option_index)
        if error:
            return None, error
        if normalized['id'] in option_ids:
            return None, validation_error(
                f'{path}.options contains duplicate ids', f'{path}.options'
            )
        option_ids.add(normalized['id'])
        options.append(normalized)

    return {
        'id': question_id,
        'type': question_type,
        'title': title,
        'description': description,
        'required': required,
        'options': options,
    }, None


def normalize_schema(schema):
    if not isinstance(schema, dict):
        return None, validation_error('schema must be an object', 'schema')
    unknown = set(schema) - SCHEMA_FIELDS
    if unknown:
        return None, validation_error(
            f'schema contains unsupported fields: {", ".join(sorted(unknown))}', 'schema'
        )
    schema_version = schema.get('schemaVersion')
    if isinstance(schema_version, bool) or schema_version != 1:
        return None, validation_error('schemaVersion must be 1', 'schema.schemaVersion')

    raw_questions = schema.get('questions')
    if not isinstance(raw_questions, list):
        return None, validation_error('schema.questions must be a list', 'schema.questions')
    if len(raw_questions) > MAX_QUESTIONS:
        return None, validation_error(
            f'schema.questions cannot contain more than {MAX_QUESTIONS} items',
            'schema.questions',
        )

    questions = []
    question_ids = set()
    for index, question in enumerate(raw_questions):
        normalized, error = normalize_question(question, index)
        if error:
            return None, error
        if normalized['id'] in question_ids:
            return None, validation_error(
                'schema.questions contains duplicate ids', 'schema.questions'
            )
        question_ids.add(normalized['id'])
        questions.append(normalized)

    return {'schemaVersion': 1, 'questions': questions}, None


def normalize_form_payload(data, *, require_version=False):
    allowed_fields = FORM_FIELDS | ({'version'} if require_version else set())
    unknown = set(data) - allowed_fields
    if unknown:
        return None, validation_error(
            f'form contains unsupported fields: {", ".join(sorted(unknown))}'
        )

    title, error = read_string(data.get('title'), 'title', required=True, max_length=120)
    if error:
        return None, error
    description, error = read_string(
        data.get('description'), 'description', max_length=1000
    )
    if error:
        return None, error
    schema, error = normalize_schema(data.get('schema'))
    if error:
        return None, error

    settlement_at, error = read_settlement_at(data.get('settlementAt'))
    if error:
        return None, error

    payload = {
        'title': title,
        'description': description,
        'definition': schema,
        'settlement_at': settlement_at,
    }
    if require_version:
        version = data.get('version')
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            return None, validation_error(
                'version must be a positive integer', 'version'
            )
        payload['expected_version'] = version
    return payload, None


def is_form_settled(form, now=None):
    now = now or taipei_now()
    return form.settled_at is not None or (
        form.settlement_at is not None and form.settlement_at <= now
    )


def serialize_form(form):
    return {
        'id': form.id,
        'title': form.title,
        'description': form.description,
        'schema': form.definition,
        'version': form.version,
        'settlementAt': to_taipei_iso(form.settlement_at),
        'settledAt': to_taipei_iso(form.settled_at),
        'settled': is_form_settled(form),
        'createdBy': form.created_by.display_username if form.created_by else None,
        'created_by_id': form.created_by_id,
        'created_at': to_taipei_iso(form.created_at),
        'updated_at': to_taipei_iso(form.updated_at),
    }


def get_form_or_error(form_id):
    form = db.session.get(FormTemplate, form_id)
    if form is None:
        return None, (jsonify({'error': 'form not found', 'code': 'not_found'}), 404)
    return form, None


@forms_bp.route('/admin/forms', methods=['GET'])
@admin_required
def list_forms():
    forms = FormTemplate.query.order_by(
        FormTemplate.updated_at.desc(), FormTemplate.id.desc()
    ).all()
    response = jsonify([serialize_form(form) for form in forms])
    response.headers['Cache-Control'] = 'no-store'
    return response


@forms_bp.route('/admin/forms/<int:form_id>', methods=['GET'])
@admin_required
def get_form(form_id):
    form, error = get_form_or_error(form_id)
    if error:
        return error
    response = jsonify(serialize_form(form))
    response.headers['Cache-Control'] = 'no-store'
    return response


@forms_bp.route('/admin/forms', methods=['POST'])
@admin_required
@limiter.limit('30 per minute', key_func=authenticated_user_rate_limit_key)
def create_form():
    data, error = read_limited_json()
    if error:
        return error
    payload, error = normalize_form_payload(data)
    if error:
        return error

    form = FormTemplate(
        title=payload['title'],
        description=payload['description'],
        definition=payload['definition'],
        settlement_at=payload['settlement_at'],
        created_by_id=g.current_user.id,
    )
    db.session.add(form)
    db.session.commit()
    return jsonify(serialize_form(form)), 201


@forms_bp.route('/admin/forms/<int:form_id>', methods=['PUT'])
@admin_required
@limiter.limit('60 per minute', key_func=authenticated_user_rate_limit_key)
def update_form(form_id):
    form, error = get_form_or_error(form_id)
    if error:
        return error
    data, error = read_limited_json()
    if error:
        return error
    payload, error = normalize_form_payload(data, require_version=True)
    if error:
        return error
    if payload['expected_version'] != form.version:
        return jsonify({
            'error': 'form was modified by another administrator',
            'code': 'version_conflict',
            'currentVersion': form.version,
        }), 409

    next_version = form.version + 1
    updated_rows = FormTemplate.query.filter_by(
        id=form.id, version=form.version
    ).update(
        {
            'title': payload['title'],
            'description': payload['description'],
            'definition': payload['definition'],
            'settlement_at': payload['settlement_at'],
            'version': next_version,
            'updated_at': taipei_now(),
        },
        synchronize_session=False,
    )
    if updated_rows != 1:
        db.session.rollback()
        current = db.session.get(FormTemplate, form_id)
        return jsonify({
            'error': 'form was modified by another administrator',
            'code': 'version_conflict',
            'currentVersion': current.version if current else None,
        }), 409
    db.session.commit()
    db.session.expire_all()
    form = db.session.get(FormTemplate, form_id)
    return jsonify(serialize_form(form))


@forms_bp.route('/admin/forms/<int:form_id>/settle', methods=['POST'])
@admin_required
@limiter.limit('30 per minute', key_func=authenticated_user_rate_limit_key)
def settle_form(form_id):
    """Close a form immediately; repeated calls return the same settled state."""
    form, error = get_form_or_error(form_id)
    if error:
        return error
    if form.settled_at is None:
        form.settled_at = taipei_now()
        db.session.commit()
    return jsonify(serialize_form(form))


@forms_bp.route('/admin/forms/<int:form_id>', methods=['DELETE'])
@admin_required
@limiter.limit('30 per minute', key_func=authenticated_user_rate_limit_key)
def delete_form(form_id):
    form, error = get_form_or_error(form_id)
    if error:
        return error
    db.session.delete(form)
    db.session.commit()
    return jsonify({'message': 'form deleted', 'id': form_id})
