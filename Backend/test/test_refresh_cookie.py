from uuid import uuid4

from werkzeug.security import generate_password_hash
from flask_jwt_extended import decode_token

from models import RefreshToken, User, db


def create_verified_user(app):
    suffix = uuid4().hex
    with app.app_context():
        user = User(
            username=f"refresh-{suffix}",
            email=f"refresh-{suffix}@example.com",
            password=generate_password_hash("StrongPass123!"),
            email_verified=True,
        )
        db.session.add(user)
        db.session.commit()
        return user.username


def login(client, username):
    return client.post(
        "/api/login",
        json={"username": username, "password": "StrongPass123!", "remember_me": True},
        environ_base={"REMOTE_ADDR": "198.51.100.42"},
    )


def test_login_sets_httponly_refresh_cookie_instead_of_returning_token(app, client):
    response = login(client, create_verified_user(app))

    assert response.status_code == 200
    assert "refresh_token" not in response.get_json()
    cookies = response.headers.getlist("Set-Cookie")
    refresh_cookie = next(cookie for cookie in cookies if cookie.startswith("refresh_token_cookie="))
    assert "HttpOnly" in refresh_cookie
    assert "SameSite=Lax" in refresh_cookie
    assert "Path=/api/refresh" in refresh_cookie


def test_refresh_requires_cookie_csrf_header(app, client):
    login(client, create_verified_user(app))

    missing_csrf = client.post("/api/refresh")
    assert missing_csrf.status_code == 401

    csrf_cookie = client.get_cookie("csrf_refresh_token")
    refreshed = client.post(
        "/api/refresh",
        headers={"X-CSRF-TOKEN": csrf_cookie.value},
    )
    assert refreshed.status_code == 200
    assert refreshed.get_json()["access_token"]


def test_refresh_rotates_cookie_and_revokes_previous_token(app, client):
    login(client, create_verified_user(app))
    old_refresh = client.get_cookie("refresh_token_cookie", path="/api/refresh").value
    old_csrf = client.get_cookie("csrf_refresh_token").value

    refreshed = client.post(
        "/api/refresh",
        headers={"X-CSRF-TOKEN": old_csrf},
    )

    assert refreshed.status_code == 200
    new_refresh = client.get_cookie("refresh_token_cookie", path="/api/refresh").value
    assert new_refresh != old_refresh

    with app.app_context():
        old_record = RefreshToken.query.filter_by(jti=decode_token(old_refresh)["jti"]).one()
        new_record = RefreshToken.query.filter_by(jti=decode_token(new_refresh)["jti"]).one()
        assert old_record.revoked_at is not None
        assert old_record.replaced_by_jti == new_record.jti
        assert old_record.family_id == new_record.family_id
        assert new_record.revoked_at is None


def test_replayed_refresh_token_revokes_its_rotated_family(app, client):
    login(client, create_verified_user(app))
    stolen_refresh = client.get_cookie("refresh_token_cookie", path="/api/refresh").value
    stolen_csrf = client.get_cookie("csrf_refresh_token").value
    assert client.post(
        "/api/refresh",
        headers={"X-CSRF-TOKEN": stolen_csrf},
    ).status_code == 200
    rotated_csrf = client.get_cookie("csrf_refresh_token").value

    attacker = app.test_client()
    attacker.set_cookie("refresh_token_cookie", stolen_refresh, path="/api/refresh")
    attacker.set_cookie("csrf_refresh_token", stolen_csrf)
    replay = attacker.post(
        "/api/refresh",
        headers={"X-CSRF-TOKEN": stolen_csrf},
    )

    assert replay.status_code == 401
    assert replay.get_json()["error"] == "Refresh token reuse detected"

    rejected = client.post(
        "/api/refresh",
        headers={"X-CSRF-TOKEN": rotated_csrf},
    )
    assert rejected.status_code == 401
    assert rejected.get_json()["error"] == "Refresh token reuse detected"


def test_logout_clears_refresh_and_csrf_cookies(app, client):
    login(client, create_verified_user(app))
    refresh_token = client.get_cookie("refresh_token_cookie", path="/api/refresh").value

    response = client.delete("/api/refresh")

    assert response.status_code == 200
    assert client.get_cookie("refresh_token_cookie", path="/api/refresh") is None
    assert client.get_cookie("csrf_refresh_token") is None
    with app.app_context():
        record = RefreshToken.query.filter_by(jti=decode_token(refresh_token)["jti"]).one()
        assert record.revoked_at is not None


def test_production_refresh_cookie_is_secure():
    from config import ProductionConfig

    assert ProductionConfig.JWT_COOKIE_SECURE is True
