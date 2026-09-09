import json

from flask import request

from log_writer import get_backend_logger
from time_utils import taipei_now, to_taipei_iso


account_logger = get_backend_logger('account', 'account.log', message_only=True)


def get_client_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()


def log_account_event(action, user, **payload):
    log_payload = {
        'event': 'account',
        'action': action,
        'status': 'success',
        'logged_at': to_taipei_iso(taipei_now()),
        'user_id': user.id,
        'username': user.username,
        'nickname': user.nickname or '-',
        'role': user.role,
        'ip': get_client_ip(),
        **payload,
    }
    account_logger.info(json.dumps(log_payload, ensure_ascii=False))
