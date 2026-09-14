import math
from copy import deepcopy
from datetime import date

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError

from models import FormSubmission, FormTemplate, db
from rate_limit import (
    authenticated_user_rate_limit_key,
    limiter,
    member_write_rate_limited,
)
from routes.admin.forms import (
    CHOICE_TYPES,
    MAX_PAYLOAD_BYTES,
    is_form_settled,
    serialize_form,
)
from routes.auth.utils import get_current_user_from_token
from time_utils import to_taipei_iso


user_forms_bp = Blueprint('user_forms', __name__)
ANSWER_FIELDS = {'formVersion', 'answers'}
MAX_SHORT_TEXT_LENGTH = 1000
MAX_LONG_TEXT_LENGTH = 10000


def answer_error(message, field=None, status=400, code='invalid_answers'):
    body = {'error': message, 'code': code}
    if field:
        body['field'] = field
    return jsonify(body), status


def current_user_or_error():
    user = get_current_user_from_token()
    if user is None:
        return None, (jsonify({'error': 'User not found'}), 404)
    return user, None


def serialize_user_form(form, submission=None):
    result = serialize_form(form)
    result.pop('createdBy', None)
    result.pop('created_by_id', None)
    result['submitted'] = submission is not None
    result['submittedAt'] = (
        to_taipei_iso(submission.submitted_at) if submission else None
    )
    return result


def is_empty(value):
    return value is None or value == '' or value == []


def normalize_answer(question, value, field):
    question_type = question['type']
    if is_empty(value):
        if question.get('required'):
            return None, f'{field} is required'
        return None, None

    if question_type in {'short_text', 'long_text'}:
        if not isinstance(value, str):
            return None, f'{field} must be a string'
        value = value.strip()
        limit = (
            MAX_SHORT_TEXT_LENGTH
            if question_type == 'short_text'
            else MAX_LONG_TEXT_LENGTH
        )
        if len(value) > limit:
            return None, f'{field} must be at most {limit} characters'
        if any(ord(character) < 32 and character not in '\n\r\t' for character in value):
            return None, f'{field} contains invalid characters'
        if question.get('required') and not value:
            return None, f'{field} is required'
        return value or None, None

    if question_type == 'number':
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None, f'{field} must be a number'
        try:
            finite = math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            return None, f'{field} must be a finite number'
        return value, None

    if question_type == 'date':
        if not isinstance(value, str):
            return None, f'{field} must be an ISO date'
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            return None, f'{field} must be an ISO date'
        if parsed.isoformat() != value:
            return None, f'{field} must be an ISO date'
        return value, None

    if question_type == 'boolean':
        if not isinstance(value, bool):
            return None, f'{field} must be a boolean'
        return value, None

    option_ids = {option['id'] for option in question.get('options', [])}
    if question_type == 'multiple_choice':
        if not isinstance(value, list) or isinstance(value, str):
            return None, f'{field} must be a list'
        if any(not isinstance(item, str) or item not in option_ids for item in value):
            return None, f'{field} contains an invalid option'
        if len(value) != len(set(value)):
            return None, f'{field} contains an invalid option'
        if question.get('required') and not value:
            return None, f'{field} is required'
        return value, None

    if question_type in CHOICE_TYPES:
        if not isinstance(value, str) or value not in option_ids:
            return None, f'{field} contains an invalid option'
        return value, None

    return None, f'{field} has an unsupported question type'


def normalize_submission(form, payload):
    if not isinstance(payload, dict):
        return None, ('submission must be an object', None)
    unknown = set(payload) - ANSWER_FIELDS
    if unknown:
        return None, (
            f'submission contains unsupported fields: {", ".join(sorted(unknown))}',
            None,
        )
    version = payload.get('formVersion')
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        return None, ('formVersion must be a positive integer', 'formVersion')
    if version != form.version:
        return None, ('form has changed; reload it before submitting', 'formVersion')
    answers = payload.get('answers')
    if not isinstance(answers, dict):
        return None, ('answers must be an object', 'answers')

    questions = form.definition.get('questions', [])
    question_ids = {question['id'] for question in questions}
    unknown_answers = set(answers) - question_ids
    if unknown_answers:
        return None, ('answers contains unknown question ids', 'answers')

    normalized = {}
    for question in questions:
        question_id = question['id']
        field = f'answers.{question_id}'
        value, error = normalize_answer(question, answers.get(question_id), field)
        if error:
            return None, (error, field)
        normalized[question_id] = value
    return normalized, None


@user_forms_bp.route('/forms', methods=['GET'])
@jwt_required()
def list_user_forms():
    user, error = current_user_or_error()
    if error:
        return error
    forms = FormTemplate.query.order_by(
        FormTemplate.updated_at.desc(), FormTemplate.id.desc()
    ).all()
    submissions = FormSubmission.query.filter(
        FormSubmission.user_id == user.id,
        FormSubmission.form_id.in_([form.id for form in forms]),
    ).all() if forms else []
    by_version = {
        (submission.form_id, submission.form_version): submission
        for submission in submissions
    }
    response = jsonify([
        serialize_user_form(form, by_version.get((form.id, form.version)))
        for form in forms
    ])
    response.headers['Cache-Control'] = 'no-store'
    return response


@user_forms_bp.route('/forms/<int:form_id>/submissions', methods=['POST'])
@jwt_required()
@limiter.limit('10 per minute', key_func=authenticated_user_rate_limit_key)
@member_write_rate_limited
def submit_form(form_id):
    user, error = current_user_or_error()
    if error:
        return error
    form = db.session.get(FormTemplate, form_id)
    if form is None:
        return answer_error('form not found', status=404, code='not_found')
    if is_form_settled(form):
        return answer_error(
            'this form has been settled', status=409, code='form_settled'
        )
    if request.content_length is not None and request.content_length > MAX_PAYLOAD_BYTES:
        return answer_error('submission payload is too large', status=413, code='payload_too_large')
    if not request.is_json:
        return answer_error(
            'Content-Type must be application/json', status=415,
            code='unsupported_media_type',
        )
    raw_body = request.get_data(cache=True)
    if len(raw_body) > MAX_PAYLOAD_BYTES:
        return answer_error('submission payload is too large', status=413, code='payload_too_large')

    answers, error = normalize_submission(form, request.get_json(silent=True))
    if error:
        message, field = error
        if field == 'formVersion' and 'changed' in message:
            return answer_error(message, field, status=409, code='version_conflict')
        return answer_error(message, field)

    existing = FormSubmission.query.filter_by(
        form_id=form.id, user_id=user.id, form_version=form.version
    ).first()
    if existing:
        return answer_error(
            'this form version has already been submitted', status=409,
            code='already_submitted',
        )

    submission = FormSubmission(
        form_id=form.id,
        user_id=user.id,
        form_version=form.version,
        form_snapshot={
            'title': form.title,
            'description': form.description,
            'schema': deepcopy(form.definition),
        },
        answers=answers,
    )
    db.session.add(submission)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return answer_error(
            'this form version has already been submitted', status=409,
            code='already_submitted',
        )
    return jsonify({
        'id': submission.id,
        'formId': form.id,
        'formVersion': submission.form_version,
        'submittedAt': to_taipei_iso(submission.submitted_at),
    }), 201
