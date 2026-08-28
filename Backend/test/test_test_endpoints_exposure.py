from flask import Flask

import pytest

from app import register_test_utils, resolve_config_name


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
