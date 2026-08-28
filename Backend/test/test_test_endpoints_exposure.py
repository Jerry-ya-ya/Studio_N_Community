from flask import Flask

from app import register_test_utils


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
