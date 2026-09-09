import json

from flask import request

from log_writer import get_backend_logger
from time_utils import taipei_now, to_taipei_iso


security_logger = get_backend_logger('security', 'security.log', message_only=True)


def get_client_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()


def log_security_event(action, user=None, **payload):
    log_payload = {
        'event': 'security',
        'action': action,
        'status': 'success',
        'logged_at': to_taipei_iso(taipei_now()),
        'user_id': user.id if user else None,
        'username': user.username if user else 'Anonymous',
        'email': user.email if user else '-',
        'nickname': (user.nickname or '-') if user else '-',
        'role': user.role if user else '-',
        'ip': get_client_ip(),
        **payload,
    }
    security_logger.info(json.dumps(log_payload, ensure_ascii=False))
