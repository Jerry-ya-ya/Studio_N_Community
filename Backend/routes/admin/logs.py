from pathlib import Path
import json
import re

from flask import Blueprint, jsonify, request

from log_writer import LOG_DIR
from routes.admin.decorators import superadmin_required

logs_bp = Blueprint('logs', __name__)

LOG_LINE_PATTERN = re.compile(r'^(?P<time>.*?) - (?P<level>[A-Z]+) - (?P<message>.*)$')
REGISTER_FIELD_PATTERN = re.compile(r'(\w+)=([^\s]+)')


def read_recent_lines(path, limit):
    if not path.exists():
        return []

    with path.open('r', encoding='utf-8') as log_file:
        lines = log_file.readlines()

    return [line.strip() for line in lines[-limit:] if line.strip()]


def read_backend_log(filename, limit):
    log_path = Path(LOG_DIR) / filename
    lines = read_recent_lines(log_path, limit)
    if lines:
        return log_path, lines

    fallback_path = Path.cwd() / 'logs' / filename
    fallback_lines = read_recent_lines(fallback_path, limit)
    if fallback_lines:
        return fallback_path, fallback_lines

    return log_path, []


def read_limit():
    try:
        limit = int(request.args.get('limit', 50))
    except (TypeError, ValueError):
        limit = 50

    return min(max(limit, 1), 200)


def parse_register_log_line(line):
    try:
        payload = json.loads(line)
        return parse_register_json_log(payload, line)
    except (TypeError, ValueError):
        pass

    match = LOG_LINE_PATTERN.match(line)
    if not match:
        return {
            'actor': 'Register',
            'action': 'recorded event',
            'target': line,
            'time': '-',
            'status': 'notice',
            'rawJson': None,
            'raw_json': None,
            'raw': line,
        }

    message = match.group('message')
    fields = dict(REGISTER_FIELD_PATTERN.findall(message))
    username = fields.get('username') or 'Unknown'
    email = fields.get('email') or '-'
    user_id = fields.get('user_id')
    role = fields.get('role') or '-'
    ip = fields.get('ip') or '-'

    if message.startswith('Register success'):
        action = 'completed registration'
        target = f'{email} / {role} / IP {ip}'
        status = 'success'
    elif 'missing required fields' in message:
        action = 'failed registration: missing fields'
        target = f'{email} / IP {ip}'
        status = 'pending'
    elif 'username exists' in message:
        action = 'failed registration: username exists'
        target = f'{email} / IP {ip}'
        status = 'notice'
    elif 'email exists' in message:
        action = 'failed registration: email exists'
        target = f'{email} / IP {ip}'
        status = 'notice'
    else:
        action = 'recorded registration event'
        target = f'{email} / IP {ip}'
        status = 'notice'

    return {
        'id': f'legacy-{abs(hash(line))}',
        'actor': username,
        'action': action,
        'target': f'#{user_id} {target}' if user_id else target,
        'time': match.group('time'),
        'status': status,
        'ip': ip,
        'rawJson': None,
        'raw_json': None,
        'raw': line,
    }


def parse_register_json_log(payload, raw_line):
    status = payload.get('status') or 'notice'
    reason = payload.get('reason') or '-'
    username = payload.get('username') or 'Register'
    email = payload.get('email') or '-'
    role = payload.get('role') or '-'
    ip = payload.get('ip') or '-'
    user_id = payload.get('user_id')

    if status == 'success':
        action = 'completed registration'
        row_status = 'success'
    else:
        action = f'failed registration: {reason}'
        row_status = 'pending' if reason == 'missing_required_fields' else 'notice'

    target = f'{email} / {role} / IP {ip}'
    if user_id:
        target = f'#{user_id} {target}'

    return {
        'id': f"{payload.get('logged_at') or payload.get('created_at') or '-'}-{payload.get('user_id') or payload.get('username') or 'register'}",
        'actor': username,
        'action': action,
        'target': target,
        'time': payload.get('logged_at') or payload.get('created_at') or '-',
        'status': row_status,
        'ip': ip,
        'rawJson': payload,
        'raw_json': payload,
        'raw': raw_line,
    }


def parse_project_log_line(line):
    try:
        payload = json.loads(line)
    except (TypeError, ValueError):
        return {
            'id': f'legacy-project-{abs(hash(line))}',
            'actor': 'Project',
            'action': 'recorded project event',
            'target': line,
            'time': '-',
            'status': 'notice',
            'rawJson': None,
            'raw_json': None,
            'raw': line,
        }

    status = payload.get('status') or 'notice'
    reason = payload.get('reason') or '-'
    username = payload.get('username') or 'Project leader'
    title = payload.get('title') or '-'
    project_id = payload.get('project_id')
    ip = payload.get('ip') or '-'
    role_needed = payload.get('role_needed') or '-'
    max_members = payload.get('max_members') or '-'

    if status == 'success':
        action = 'created project recruitment'
        row_status = 'success'
    else:
        action = f'failed project recruitment: {reason}'
        row_status = 'pending'

    target = f'{title} / role {role_needed} / max {max_members} / IP {ip}'
    if project_id:
        target = f'#{project_id} {target}'

    return {
        'id': f"{payload.get('logged_at') or payload.get('created_at') or '-'}-{payload.get('project_id') or payload.get('creator_id') or payload.get('username') or 'project'}",
        'actor': username,
        'action': action,
        'target': target,
        'time': payload.get('logged_at') or payload.get('created_at') or '-',
        'status': row_status,
        'ip': ip,
        'rawJson': payload,
        'raw_json': payload,
        'raw': line,
    }


@logs_bp.route('/superadmin/logs/register', methods=['GET'])
@superadmin_required
def register_logs():
    limit = read_limit()
    log_path, lines = read_backend_log('register.log', limit)

    items = [parse_register_log_line(line) for line in reversed(lines)]

    response = jsonify({
        'type': 'register',
        'path': str(log_path),
        'count': len(lines),
        'items': items,
    })
    response.headers['Cache-Control'] = 'no-store'
    return response


@logs_bp.route('/superadmin/logs/project', methods=['GET'])
@superadmin_required
def project_logs():
    limit = read_limit()
    log_path, lines = read_backend_log('project.log', limit)
    items = [parse_project_log_line(line) for line in reversed(lines)]

    response = jsonify({
        'type': 'project',
        'path': str(log_path),
        'count': len(lines),
        'items': items,
    })
    response.headers['Cache-Control'] = 'no-store'
    return response
