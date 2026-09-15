from collections import Counter

from flask import Blueprint, jsonify

from models import FormSubmission, FormTemplate, db
from routes.admin.decorators import superadmin_required
from routes.admin.forms import is_form_settled
from time_utils import taipei_now, to_taipei_iso


form_statistics_bp = Blueprint('form_statistics', __name__)


def _percentage(count, total):
    return round((count / total) * 100, 1) if total else 0.0


def _choice_breakdown(question, answers, response_count):
    counts = Counter()
    for answer in answers:
        values = answer if isinstance(answer, list) else [answer]
        counts.update(value for value in values if isinstance(value, str))

    return [
        {
            'id': option['id'],
            'label': option['label'],
            'count': counts[option['id']],
            'percentage': _percentage(counts[option['id']], response_count),
        }
        for option in question.get('options', [])
    ]


def _question_statistics(question, submissions):
    answers = [
        submission.answers.get(question['id'])
        for submission in submissions
        if submission.answers.get(question['id']) not in (None, '', [])
    ]
    response_count = len(answers)
    result = {
        'id': question['id'],
        'title': question['title'],
        'type': question['type'],
        'required': bool(question.get('required')),
        'responseCount': response_count,
        'missingCount': len(submissions) - response_count,
        'options': [],
        'numberSummary': None,
    }

    if question['type'] in {'single_choice', 'multiple_choice', 'dropdown'}:
        result['options'] = _choice_breakdown(question, answers, response_count)
    elif question['type'] == 'boolean':
        true_count = sum(answer is True for answer in answers)
        false_count = sum(answer is False for answer in answers)
        result['options'] = [
            {
                'id': 'true', 'label': 'Yes', 'count': true_count,
                'percentage': _percentage(true_count, response_count),
            },
            {
                'id': 'false', 'label': 'No', 'count': false_count,
                'percentage': _percentage(false_count, response_count),
            },
        ]
    elif question['type'] == 'number' and answers:
        numeric_answers = [
            float(answer) for answer in answers
            if isinstance(answer, (int, float)) and not isinstance(answer, bool)
        ]
        if numeric_answers:
            result['numberSummary'] = {
                'minimum': min(numeric_answers),
                'maximum': max(numeric_answers),
                'average': round(sum(numeric_answers) / len(numeric_answers), 2),
            }

    return result


def build_form_statistics(form, submissions, generated_at):
    current_submissions = [
        submission for submission in submissions
        if submission.form_version == form.version
    ]
    settled = is_form_settled(form, generated_at)
    final_at = form.settled_at or (form.settlement_at if settled else None)
    questions = form.definition.get('questions', [])
    return {
        'id': form.id,
        'title': form.title,
        'version': form.version,
        'settled': settled,
        'settlementAt': to_taipei_iso(form.settlement_at),
        'settledAt': to_taipei_iso(form.settled_at),
        'finalizedAt': to_taipei_iso(final_at),
        'submissionCount': len(current_submissions),
        'historicalSubmissionCount': len(submissions) - len(current_submissions),
        'questionCount': len(questions),
        'questions': [
            _question_statistics(question, current_submissions)
            for question in questions
        ],
    }


@form_statistics_bp.route('/superadmin/form-statistics', methods=['GET'])
@superadmin_required
def get_form_statistics():
    """Return a fresh aggregate; settled forms are therefore calculated one final time."""
    generated_at = taipei_now()
    forms = FormTemplate.query.order_by(
        FormTemplate.updated_at.desc(), FormTemplate.id.desc()
    ).all()
    submissions = FormSubmission.query.order_by(FormSubmission.id.asc()).all()
    submissions_by_form = {}
    for submission in submissions:
        submissions_by_form.setdefault(submission.form_id, []).append(submission)

    form_results = [
        build_form_statistics(
            form, submissions_by_form.get(form.id, []), generated_at
        )
        for form in forms
    ]
    response = jsonify({
        'generatedAt': to_taipei_iso(generated_at),
        'summary': {
            'totalForms': len(forms),
            'openForms': sum(not form['settled'] for form in form_results),
            'settledForms': sum(form['settled'] for form in form_results),
            'totalSubmissions': db.session.query(FormSubmission.id).count(),
            'uniqueRespondents': db.session.query(
                db.func.count(db.distinct(FormSubmission.user_id))
            ).scalar() or 0,
        },
        'forms': form_results,
    })
    response.headers['Cache-Control'] = 'no-store'
    return response
