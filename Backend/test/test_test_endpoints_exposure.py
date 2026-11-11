from flask import Flask

import pytest

from app import configure_trusted_proxy, register_test_utils, resolve_config_name
from models import User, db


@pytest.fixture
def test_api_app():
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
    )
    db.init_app(app)
    register_test_utils(app)

    with app.app_context():
        db.create_all()
        db.session.add(User(username="e2e-user", password="unused", email="e2e@example.com"))
        db.session.commit()

    return app


@pytest.mark.parametrize(
    ("configured_token", "provided_token", "status"),
    [
        ("", "a" * 64, 404),
        ("short", "short", 404),
        ("a" * 64, None, 403),
        ("a" * 64, "b" * 64, 403),
    ],
)
def test_test_api_denies_unauthorized_mutations(test_api_app, configured_token, provided_token, status):
    test_api_app.config["E2E_TEST_TOKEN"] = configured_token
    headers = {"X-E2E-Test-Token": provided_token} if provided_token is not None else {}
    client = test_api_app.test_client()

    assert client.post("/api/test/clear-db", headers=headers).status_code == status
    response = client.post("/api/test/verify-user", headers=headers, json={"email": "e2e@example.com"})
    assert response.status_code == status
    with test_api_app.app_context():
        assert User.query.one().email_verified is False


def test_test_api_accepts_the_configured_token(test_api_app):
    token = "a" * 64
    test_api_app.config["E2E_TEST_TOKEN"] = token
    headers = {"X-E2E-Test-Token": token}
    client = test_api_app.test_client()

    response = client.post("/api/test/verify-user", headers=headers, json={"email": "e2e@example.com"})
    assert response.status_code == 200
    with test_api_app.app_context():
        assert User.query.one().email_verified is True

    assert client.post("/api/test/clear-db", headers=headers).status_code == 200
    with test_api_app.app_context():
        assert User.query.count() == 0


def test_destructive_test_endpoints_are_not_registered_by_default():
    app = Flask(__name__)
    register_test_utils(app)

    rules = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/test/clear-db" not in rules
    assert "/api/test/verify-user" not in rules


def test_destructive_test_endpoints_are_registered_only_in_testing_mode():
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_test_utils(app)

    rules = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/test/clear-db" in rules
    assert "/api/test/verify-user" in rules


def test_destructive_test_endpoints_are_not_registered_in_production_mode():
    app = Flask(__name__)
    app.config.update(TESTING=False, E2E_TEST_TOKEN="a" * 64)
    register_test_utils(app)

    rules = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/test/clear-db" not in rules
    assert "/api/test/verify-user" not in rules


def test_explicit_production_config_is_authoritative(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "development")

    assert resolve_config_name("production") == "production"


def test_unknown_environment_is_rejected(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "typo")

    with pytest.raises(RuntimeError, match="Invalid FLASK_ENV"):
        resolve_config_name("none")


def test_production_proxy_uses_forwarded_client_address():
    app = Flask(__name__)
    app.config["TRUSTED_PROXY_HOPS"] = 1
    configure_trusted_proxy(app)

    @app.get("/client-ip")
    def client_ip():
        from flask import request

        return {"ip": request.remote_addr, "scheme": request.scheme}

    response = app.test_client().get(
        "/client-ip",
        headers={
            "X-Forwarded-For": "203.0.113.25",
            "X-Forwarded-Proto": "https",
        },
        environ_overrides={"REMOTE_ADDR": "172.20.0.2"},
    )

    assert response.get_json() == {"ip": "203.0.113.25", "scheme": "https"}
