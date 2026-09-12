from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token

from models import User, db
from rate_limit import MEMBER_WRITE_RATE_LIMIT, limiter


def bearer(token):
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture()
def write_limit_accounts(app):
    suffix = uuid4().hex
    with app.app_context():
        limiter.reset()
        users = [
            User(
                username=f'write-limit-{index}-{suffix}',
                email=f'write-limit-{index}-{suffix}@example.com',
                password='test-password',
                email_verified=True,
            )
            for index in range(2)
        ]
        db.session.add_all(users)
        db.session.commit()
        result = {
            'user_ids': [user.id for user in users],
            'tokens': [create_access_token(identity=str(user.id)) for user in users],
        }

    yield result

    with app.app_context():
        limiter.reset()
        User.query.filter(User.id.in_(result['user_ids'])).delete(
            synchronize_session=False
        )
        db.session.commit()


def test_resource_writes_share_a_per_member_rate_limit(
    client, write_limit_accounts
):
    allowed_requests = int(MEMBER_WRITE_RATE_LIMIT.split()[0])
    first_headers = bearer(write_limit_accounts['tokens'][0])

    for _ in range(allowed_requests):
        response = client.post('/api/post', json={}, headers=first_headers)
        assert response.status_code == 400

    limited = client.post(
        '/api/friends/request', json={}, headers=first_headers
    )
    assert limited.status_code == 429
    assert limited.get_json() == {
        'error': '請求過於頻繁，請稍後再試',
        'code': 'rate_limit_exceeded',
    }

    # The shared quota is keyed by authenticated member, not source address.
    other_member = client.post(
        '/api/friends/request',
        json={},
        headers=bearer(write_limit_accounts['tokens'][1]),
    )
    assert other_member.status_code == 400
