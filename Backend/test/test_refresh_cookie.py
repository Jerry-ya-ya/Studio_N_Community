from uuid import uuid4

from werkzeug.security import generate_password_hash

from models import User, db


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


def test_logout_clears_refresh_and_csrf_cookies(app, client):
    login(client, create_verified_user(app))

    response = client.delete("/api/refresh")

    assert response.status_code == 200
    assert client.get_cookie("refresh_token_cookie", path="/api/refresh") is None
    assert client.get_cookie("csrf_refresh_token") is None


def test_production_refresh_cookie_is_secure():
    from config import ProductionConfig

    assert ProductionConfig.JWT_COOKIE_SECURE is True
