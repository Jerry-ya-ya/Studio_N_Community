from pathlib import Path
import json
import re

from flask import Blueprint, jsonify, request

from log_writer import LOG_DIR
from routes.admin.decorators import admin_required, superadmin_required

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


def parse_sign_in_log_line(line):
    try:
        payload = json.loads(line)
    except (TypeError, ValueError):
        return {
            'id': f'legacy-sign-in-{abs(hash(line))}',
            'actor': 'Sign in',
            'action': 'recorded sign in event',
            'target': line,
            'time': '-',
            'status': 'notice',
            'rawJson': None,
            'raw_json': None,
            'raw': line,
        }

    status = payload.get('status') or 'notice'
    reason = payload.get('reason') or '-'
    username = payload.get('username') or 'Sign in'
    email = payload.get('email') or '-'
    role = payload.get('role') or '-'
    ip = payload.get('ip') or '-'
    user_id = payload.get('user_id')
    remember_me = payload.get('remember_me')

    if status == 'success':
        action = 'signed in'
        row_status = 'success'
    else:
        action = f'failed sign in: {reason}'
        row_status = 'notice' if reason == 'email_unverified' else 'pending'

    remember_label = 'remember true' if remember_me else 'remember false'
    target = f'{email} / {role} / {remember_label} / IP {ip}'
    if user_id:
        target = f'#{user_id} {target}'

    return {
        'id': f"{payload.get('logged_at') or '-'}-{payload.get('user_id') or payload.get('username') or 'sign-in'}",
        'actor': username,
        'action': action,
        'target': target,
        'time': payload.get('logged_at') or '-',
        'status': row_status,
        'ip': ip,
        'rawJson': payload,
        'raw_json': payload,
        'raw': line,
    }


def parse_content_log_line(line):
    try:
        payload = json.loads(line)
    except (TypeError, ValueError):
        return {
            'id': f'legacy-content-{abs(hash(line))}',
            'actor': 'Content',
            'action': 'recorded content event',
            'target': line,
            'time': '-',
            'status': 'notice',
            'rawJson': None,
            'raw_json': None,
            'raw': line,
        }

    status = payload.get('status') or 'notice'
    action_key = payload.get('action') or 'content_event'
    reason = payload.get('reason') or '-'
    username = payload.get('username') or 'Admin'
    role = payload.get('role') or '-'
    ip = payload.get('ip') or '-'
    item_id = payload.get('item_id')
    theme = payload.get('theme') or '-'
    title = payload.get('title') or '-'
    item_count = payload.get('item_count')

    action_labels = {
        'replace_home_news': 'saved home news content',
        'create_home_news_item': 'created home news item',
        'update_home_news_item': 'updated home news item',
        'upload_home_news_background': 'uploaded home news background',
        'delete_home_news_item': 'deleted home news item',
    }

    if status == 'success':
        action = action_labels.get(action_key, 'updated admin content')
        row_status = 'success'
    else:
        action = f'failed content update: {reason}'
        row_status = 'pending'

    if item_count is not None:
        target = f'{item_count} items / role {role} / IP {ip}'
    else:
        target = f'{theme} / {title} / role {role} / IP {ip}'
        if item_id:
            target = f'#{item_id} {target}'

    return {
        'id': f"{payload.get('logged_at') or '-'}-{payload.get('item_id') or payload.get('admin_id') or payload.get('action') or 'content'}",
        'actor': username,
        'action': action,
        'target': target,
        'time': payload.get('logged_at') or '-',
        'status': row_status,
        'ip': ip,
        'rawJson': payload,
        'raw_json': payload,
        'raw': line,
    }


def parse_news_log_line(line):
    try:
        payload = json.loads(line)
    except (TypeError, ValueError):
        return {
            'id': f'legacy-news-{abs(hash(line))}',
            'actor': 'News',
            'action': 'recorded news event',
            'target': line,
            'time': '-',
            'status': 'notice',
            'rawJson': None,
            'raw_json': None,
            'raw': line,
        }

    status = payload.get('status') or 'notice'
    action_key = payload.get('action') or 'news_event'
    reason = payload.get('reason') or '-'
    username = payload.get('username') or 'Admin'
    ip = payload.get('ip') or '-'
    item_id = payload.get('item_id')
    theme = payload.get('theme') or '-'
    title = payload.get('title') or '-'
    tag = payload.get('tag') or '-'
    item_count = payload.get('item_count')
    filename = payload.get('filename')

    action_labels = {
        'replace_home_news': 'saved news collection',
        'create_home_news_item': 'created news item',
        'update_home_news_item': 'updated news item',
        'upload_home_news_background': 'uploaded news background',
        'delete_home_news_item': 'deleted news item',
    }

    if status == 'success':
        action = action_labels.get(action_key, 'updated news')
        row_status = 'success'
    else:
        action = f'failed news update: {reason}'
        row_status = 'pending'

    if item_count is not None:
        target = f'{item_count} items / cmen {payload.get("cmen_count", "-")} / eden {payload.get("eden_count", "-")} / IP {ip}'
    else:
        target = f'{theme} / {title} / {tag} / IP {ip}'
        if filename:
            target = f'{target} / file {filename}'
        if item_id:
            target = f'#{item_id} {target}'

    return {
        'id': f"{payload.get('logged_at') or '-'}-{payload.get('item_id') or payload.get('admin_id') or payload.get('action') or 'news'}",
        'actor': username,
        'action': action,
        'target': target,
        'time': payload.get('logged_at') or '-',
        'status': row_status,
        'ip': ip,
        'rawJson': payload,
        'raw_json': payload,
        'raw': line,
    }


def build_register_logs_response():
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


@logs_bp.route('/superadmin/logs/register', methods=['GET'])
@superadmin_required
def register_logs():
    return build_register_logs_response()


@logs_bp.route('/admin/logs/register', methods=['GET'])
@admin_required
def admin_register_logs():
    return build_register_logs_response()


def build_sign_in_logs_response():
    limit = read_limit()
    log_path, lines = read_backend_log('sign_in.log', limit)
    items = [parse_sign_in_log_line(line) for line in reversed(lines)]

    response = jsonify({
        'type': 'sign-in',
        'path': str(log_path),
        'count': len(lines),
        'items': items,
    })
    response.headers['Cache-Control'] = 'no-store'
    return response


@logs_bp.route('/superadmin/logs/sign-in', methods=['GET'])
@superadmin_required
def sign_in_logs():
    return build_sign_in_logs_response()


@logs_bp.route('/admin/logs/sign-in', methods=['GET'])
@admin_required
def admin_sign_in_logs():
    return build_sign_in_logs_response()


@logs_bp.route('/superadmin/logs/content', methods=['GET'])
@superadmin_required
def content_logs():
    limit = read_limit()
    log_path, lines = read_backend_log('content.log', limit)
    items = [parse_content_log_line(line) for line in reversed(lines)]

    response = jsonify({
        'type': 'content',
        'path': str(log_path),
        'count': len(lines),
        'items': items,
    })
    response.headers['Cache-Control'] = 'no-store'
    return response


@logs_bp.route('/superadmin/logs/news', methods=['GET'])
@superadmin_required
def news_logs():
    limit = read_limit()
    log_path, lines = read_backend_log('news.log', limit)
    items = [parse_news_log_line(line) for line in reversed(lines)]

    response = jsonify({
        'type': 'news',
        'path': str(log_path),
        'count': len(lines),
        'items': items,
    })
    response.headers['Cache-Control'] = 'no-store'
    return response


def build_project_logs_response():
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


@logs_bp.route('/superadmin/logs/project', methods=['GET'])
@superadmin_required
def project_logs():
    return build_project_logs_response()


@logs_bp.route('/admin/logs/project', methods=['GET'])
@admin_required
def admin_project_logs():
    return build_project_logs_response()
