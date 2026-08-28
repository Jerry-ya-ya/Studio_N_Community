from flask import Flask

import pytest

from app import configure_trusted_proxy, register_test_utils, resolve_config_name


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
    app.config["TESTING"] = False
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
