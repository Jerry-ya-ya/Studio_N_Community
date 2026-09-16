from datetime import timedelta
from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token

from models import ApiRateLimitOverride, User, db
from rate_limit import limiter
from time_utils import taipei_now


ENDPOINT = '/api/superadmin/special-abilities/api-rate-limit'


def bearer(token):
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture()
def ability_accounts(app):
    suffix = uuid4().hex
    with app.app_context():
        limiter.reset()
        ApiRateLimitOverride.query.delete()
        users = [
            User(
                username=f'ability-root-{suffix}',
                email=f'ability-root-{suffix}@example.com',
                password='test-password',
                role='superadmin',
                email_verified=True,
            ),
            User(
                username=f'ability-admin-{suffix}',
                email=f'ability-admin-{suffix}@example.com',
                password='test-password',
                role='admin',
                email_verified=True,
            ),
        ]
        db.session.add_all(users)
        db.session.commit()
        result = {
            'user_ids': [user.id for user in users],
            'superadmin_token': create_access_token(identity=str(users[0].id)),
            'admin_token': create_access_token(identity=str(users[1].id)),
        }

    yield result

    with app.app_context():
        limiter.reset()
        ApiRateLimitOverride.query.delete()
        User.query.filter(User.id.in_(result['user_ids'])).delete(
            synchronize_session=False
        )
        db.session.commit()


def test_special_ability_requires_superadmin(client, ability_accounts):
    assert client.get(ENDPOINT).status_code == 401
    assert client.get(
        ENDPOINT, headers=bearer(ability_accounts['admin_token'])
    ).status_code == 403
    assert client.post(
        ENDPOINT,
        json={'durationMinutes': 10},
        headers=bearer(ability_accounts['admin_token']),
    ).status_code == 403


@pytest.mark.parametrize('duration', [None, True, 9, 31, 10.5, '10'])
def test_special_ability_rejects_durations_outside_integer_bounds(
    client, ability_accounts, duration
):
    response = client.post(
        ENDPOINT,
        json={'durationMinutes': duration},
        headers=bearer(ability_accounts['superadmin_token']),
    )
    assert response.status_code == 400
    assert response.get_json()['code'] == 'invalid_duration'


def test_superadmin_can_activate_a_time_bounded_override(client, ability_accounts):
    response = client.post(
        ENDPOINT,
        json={'durationMinutes': 10},
        headers=bearer(ability_accounts['superadmin_token']),
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['active'] is True
    assert payload['minimumMinutes'] == 10
    assert payload['maximumMinutes'] == 30
    assert 599 <= payload['remainingSeconds'] <= 600
    assert payload['activatedAt']
    assert payload['expiresAt']
    assert response.headers['Cache-Control'] == 'no-store'

    status = client.get(
        ENDPOINT, headers=bearer(ability_accounts['superadmin_token'])
    )
    assert status.status_code == 200
    assert status.get_json()['active'] is True


def test_active_override_skips_rate_limits_but_not_authorization(
    app, client, ability_accounts
):
    activation = client.post(
        ENDPOINT,
        json={'durationMinutes': 30},
        headers=bearer(ability_accounts['superadmin_token']),
    )
    assert activation.status_code == 200

    # The limiter filter is global for API requests while active.
    for _ in range(7):
        response = client.post(
            '/api/login',
            json={'username': 'override-login', 'password': 'wrong'},
            environ_overrides={'REMOTE_ADDR': '203.0.113.86'},
        )
        assert response.status_code == 401

    # Route authorization and every non-rate-limit control remain enforced.
    forbidden = client.get(
        ENDPOINT, headers=bearer(ability_accounts['admin_token'])
    )
    assert forbidden.status_code == 403

    with app.app_context():
        override = db.session.get(ApiRateLimitOverride, 1)
        override.expires_at = taipei_now() - timedelta(seconds=1)
        db.session.commit()
        limiter.reset()

    for _ in range(5):
        response = client.post(
            '/api/login',
            json={'username': 'expired-override-login', 'password': 'wrong'},
            environ_overrides={'REMOTE_ADDR': '203.0.113.87'},
        )
        assert response.status_code == 401
    limited = client.post(
        '/api/login',
        json={'username': 'expired-override-login', 'password': 'wrong'},
        environ_overrides={'REMOTE_ADDR': '203.0.113.87'},
    )
    assert limited.status_code == 429
