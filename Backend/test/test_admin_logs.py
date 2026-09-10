import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from routes.admin import logs


def structured(**overrides):
    payload = {
        "logged_at": "2026-09-10T12:00:00Z",
        "status": "success",
        "username": "jack",
        "ip": "203.0.113.10",
    }
    payload.update(overrides)
    return json.dumps(payload)


def test_read_recent_lines_handles_missing_files_blank_lines_and_limits(tmp_path):
    missing = tmp_path / "missing.log"
    assert logs.read_recent_lines(missing, 10) == []

    log_file = tmp_path / "events.log"
    log_file.write_text("old\n\n middle \nnew\n", encoding="utf-8")
    assert logs.read_recent_lines(log_file, 3) == ["middle", "new"]


def test_read_backend_log_prefers_configured_log_directory(tmp_path, monkeypatch):
    configured = tmp_path / "configured"
    fallback = tmp_path / "fallback" / "logs"
    configured.mkdir()
    fallback.mkdir(parents=True)
    (configured / "register.log").write_text("configured\n", encoding="utf-8")
    (fallback / "register.log").write_text("fallback\n", encoding="utf-8")
    monkeypatch.setattr(logs, "LOG_DIR", configured)
    monkeypatch.chdir(fallback.parent)

    path, lines = logs.read_backend_log("register.log", 5)

    assert path == configured / "register.log"
    assert lines == ["configured"]


def test_read_backend_log_uses_fallback_then_returns_configured_empty_path(tmp_path, monkeypatch):
    configured = tmp_path / "configured"
    working = tmp_path / "working"
    fallback = working / "logs"
    configured.mkdir()
    fallback.mkdir(parents=True)
    monkeypatch.setattr(logs, "LOG_DIR", configured)
    monkeypatch.chdir(working)
    (fallback / "news.log").write_text("fallback\n", encoding="utf-8")

    assert logs.read_backend_log("news.log", 5) == (
        fallback / "news.log",
        ["fallback"],
    )
    assert logs.read_backend_log("content.log", 5) == (
        configured / "content.log",
        [],
    )


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("", 50),
        ("?limit=bad", 50),
        ("?limit=0", 1),
        ("?limit=-10", 1),
        ("?limit=17", 17),
        ("?limit=999", 200),
    ],
)
def test_read_limit_normalizes_query_values(app, query, expected):
    with app.test_request_context(f"/{query}"):
        assert logs.read_limit() == expected


@pytest.mark.parametrize(
    ("message", "action", "status"),
    [
        ("Register success username=jack email=j@example.com role=user ip=1.2.3.4 user_id=7", "completed registration", "success"),
        ("Register failed: missing required fields email=j@example.com ip=1.2.3.4", "failed registration: missing fields", "pending"),
        ("Register failed: username exists username=jack email=j@example.com", "failed registration: username exists", "notice"),
        ("Register failed: email exists username=jack email=j@example.com", "failed registration: email exists", "notice"),
        ("Register audit username=jack", "recorded registration event", "notice"),
    ],
)
def test_parse_legacy_register_events(message, action, status):
    item = logs.parse_register_log_line(f"2026-09-10 12:00:00 - INFO - {message}")

    assert item["action"] == action
    assert item["status"] == status
    assert item["time"] == "2026-09-10 12:00:00"
    assert item["rawJson"] is None
    assert item["raw_json"] is None


def test_parse_register_handles_unstructured_and_structured_events():
    legacy = logs.parse_register_log_line("not a conventional log line")
    assert legacy == {
        "actor": "Register",
        "action": "recorded event",
        "target": "not a conventional log line",
        "time": "-",
        "status": "notice",
        "rawJson": None,
        "raw_json": None,
        "raw": "not a conventional log line",
    }

    success = logs.parse_register_log_line(structured(
        email="jack@example.com", role="admin", user_id=12
    ))
    assert success["id"] == "2026-09-10T12:00:00Z-12"
    assert success["actor"] == "jack"
    assert success["action"] == "completed registration"
    assert success["target"].startswith("#12 jack@example.com / admin")
    assert success["rawJson"] == success["raw_json"]

    failed = logs.parse_register_json_log(
        {"created_at": "now", "reason": "missing_required_fields"}, "raw"
    )
    assert failed["id"] == "now-register"
    assert failed["actor"] == "Register"
    assert failed["action"] == "failed registration: missing_required_fields"
    assert failed["status"] == "pending"

    duplicate = logs.parse_register_json_log({"reason": "email_exists"}, "raw")
    assert duplicate["status"] == "notice"
    assert duplicate["target"] == "- / - / IP -"


@pytest.mark.parametrize(
    ("parser", "prefix", "actor", "action"),
    [
        (logs.parse_project_log_line, "legacy-project-", "Project", "recorded project event"),
        (logs.parse_sign_in_log_line, "legacy-sign-in-", "Sign in", "recorded sign in event"),
        (logs.parse_content_log_line, "legacy-content-", "Content", "recorded content event"),
        (logs.parse_todo_settlement_log_line, "legacy-todo-settlement-", "Todo Settlement", "recorded settlement event"),
        (logs.parse_news_log_line, "legacy-news-", "News", "recorded news event"),
    ],
)
def test_json_log_parsers_preserve_unstructured_lines(parser, prefix, actor, action):
    item = parser("legacy text")

    assert item["id"].startswith(prefix)
    assert item["actor"] == actor
    assert item["action"] == action
    assert item["target"] == item["raw"] == "legacy text"
    assert item["rawJson"] is None
    assert item["raw_json"] is None


def test_parse_project_success_failure_and_defaults():
    success = logs.parse_project_log_line(structured(
        project_id=21, title="Beanstalk", role_needed="Backend", max_members=3
    ))
    assert success["id"] == "2026-09-10T12:00:00Z-21"
    assert success["action"] == "created project recruitment"
    assert success["target"].startswith("#21 Beanstalk / role Backend / max 3")
    assert success["status"] == "success"

    failed = logs.parse_project_log_line(structured(
        status="failed", reason="invalid", creator_id=4, username=None
    ))
    assert failed["id"].endswith("-4")
    assert failed["actor"] == "Project leader"
    assert failed["action"] == "failed project recruitment: invalid"
    assert failed["status"] == "pending"


def test_parse_sign_in_success_failure_and_remember_me():
    success = logs.parse_sign_in_log_line(structured(
        user_id=8, email="jack@example.com", role="admin", remember_me=True
    ))
    assert success["id"].endswith("-8")
    assert success["action"] == "signed in"
    assert success["target"].startswith("#8 jack@example.com / admin / remember true")
    assert success["status"] == "success"

    unverified = logs.parse_sign_in_log_line(structured(
        status="failed", reason="email_unverified", logged_at=None, username=None
    ))
    assert unverified["id"] == "--sign-in"
    assert unverified["actor"] == "Sign in"
    assert unverified["action"] == "failed sign in: email_unverified"
    assert "remember false" in unverified["target"]
    assert unverified["status"] == "notice"

    invalid = logs.parse_sign_in_log_line(structured(status="failed", reason="bad_password"))
    assert invalid["status"] == "pending"


@pytest.mark.parametrize(
    ("action_key", "expected"),
    [
        ("replace_home_news", "saved home news content"),
        ("create_home_news_item", "created home news item"),
        ("update_home_news_item", "updated home news item"),
        ("upload_home_news_background", "uploaded home news background"),
        ("delete_home_news_item", "deleted home news item"),
        ("other", "updated admin content"),
    ],
)
def test_parse_content_success_action_labels(action_key, expected):
    item = logs.parse_content_log_line(structured(
        action=action_key, item_id=3, admin_id=9, role="superadmin",
        theme="cmen", title="Story",
    ))
    assert item["action"] == expected
    assert item["target"].startswith("#3 cmen / Story / role superadmin")
    assert item["status"] == "success"


def test_parse_content_collection_failure_and_defaults():
    collection = logs.parse_content_log_line(structured(
        action="replace_home_news", item_count=0
    ))
    assert collection["target"].startswith("0 items / role -")

    failed = logs.parse_content_log_line(structured(
        status="failed", reason="invalid_payload", logged_at=None, username=None
    ))
    assert failed["id"].endswith("-content")
    assert failed["actor"] == "Admin"
    assert failed["action"] == "failed content update: invalid_payload"
    assert failed["status"] == "pending"


def test_parse_todo_settlement_success_skip_and_value_defaults():
    success = logs.parse_todo_settlement_log_line(structured(
        todo_id=5,
        settled_by_id=2,
        settled_by_nickname="Boss",
        completed_by_username="Jill",
        project_title="Castle",
        todo_text="Climb",
        reward_coins=13,
        reward_formula="5 + 6 + 2",
        priority_level=5,
        duration=2,
        difficulty=6,
    ))
    assert success["id"].endswith("-5-2")
    assert success["actor"] == "Boss"
    assert success["action"] == "settled todo reward +13 coins"
    assert success["target"].startswith("#5 Castle / Climb / completed by Jill / P5 T2 D6")
    assert success["status"] == "success"

    skipped = logs.parse_todo_settlement_log_line(structured(
        status="skipped", reason="missing_claimed_by", duration=None, difficulty=None
    ))
    assert skipped["id"].endswith("-todo-settlement")
    assert skipped["actor"] == "Admin"
    assert skipped["action"] == "skipped todo settlement: missing_claimed_by"
    assert "P- T- D- / -" in skipped["target"]
    assert skipped["status"] == "notice"


@pytest.mark.parametrize(
    ("action_key", "expected"),
    [
        ("replace_home_news", "saved news collection"),
        ("create_home_news_item", "created news item"),
        ("update_home_news_item", "updated news item"),
        ("upload_home_news_background", "uploaded news background"),
        ("delete_home_news_item", "deleted news item"),
        ("other", "updated news"),
    ],
)
def test_parse_news_success_action_labels(action_key, expected):
    item = logs.parse_news_log_line(structured(
        action=action_key, item_id=6, theme="eden", title="Giant", tag="event",
        filename="giant.png",
    ))
    assert item["action"] == expected
    assert item["target"].startswith("#6 eden / Giant / event")
    assert item["target"].endswith("file giant.png")
    assert item["status"] == "success"


def test_parse_news_collection_failure_and_defaults():
    collection = logs.parse_news_log_line(structured(
        action="replace_home_news", item_count=0, cmen_count=2, eden_count=1
    ))
    assert collection["target"].startswith("0 items / cmen 2 / eden 1")

    failed = logs.parse_news_log_line(structured(
        status="failed", reason="upload_error", logged_at=None, username=None
    ))
    assert failed["id"].endswith("-news")
    assert failed["actor"] == "Admin"
    assert failed["action"] == "failed news update: upload_error"
    assert failed["status"] == "pending"


ALL_ENDPOINTS = [
    "/api/superadmin/logs/register",
    "/api/admin/logs/register",
    "/api/superadmin/logs/sign-in",
    "/api/admin/logs/sign-in",
    "/api/superadmin/logs/content",
    "/api/superadmin/logs/news",
    "/api/superadmin/logs/todo-settlement",
    "/api/superadmin/logs/project",
    "/api/admin/logs/project",
]

SUPERADMIN_ENDPOINTS = [path for path in ALL_ENDPOINTS if "/superadmin/" in path]


@pytest.mark.parametrize("endpoint", ALL_ENDPOINTS)
def test_log_endpoints_require_authentication(client, endpoint):
    assert client.get(endpoint).status_code == 401


@pytest.mark.parametrize("endpoint", SUPERADMIN_ENDPOINTS)
def test_superadmin_log_endpoints_reject_admins(client, endpoint):
    with (
        patch("routes.admin.decorators.verify_jwt_in_request"),
        patch(
            "routes.admin.decorators.get_current_user_from_token",
            return_value=SimpleNamespace(role="admin"),
        ),
    ):
        response = client.get(endpoint)

    assert response.status_code == 403
    assert response.get_json() == {"error": "需要最高管理員權限"}


@pytest.mark.parametrize("endpoint", ALL_ENDPOINTS)
def test_log_endpoints_reject_regular_and_missing_users(client, endpoint):
    with (
        patch("routes.admin.decorators.verify_jwt_in_request"),
        patch(
            "routes.admin.decorators.get_current_user_from_token",
            return_value=SimpleNamespace(role="user"),
        ),
    ):
        assert client.get(endpoint).status_code == 403

    with (
        patch("routes.admin.decorators.verify_jwt_in_request"),
        patch("routes.admin.decorators.get_current_user_from_token", return_value=None),
    ):
        response = client.get(endpoint)

    assert response.status_code == 401
    assert response.get_json() == {"error": "使用者不存在"}


@pytest.mark.parametrize(
    ("endpoint", "filename", "log_type", "line"),
    [
        ("/api/superadmin/logs/register", "register.log", "register", structured(email="j@example.com")),
        ("/api/admin/logs/register", "register.log", "register", structured(email="j@example.com")),
        ("/api/superadmin/logs/sign-in", "sign_in.log", "sign-in", structured(email="j@example.com")),
        ("/api/admin/logs/sign-in", "sign_in.log", "sign-in", structured(email="j@example.com")),
        ("/api/superadmin/logs/content", "content.log", "content", structured(action="other")),
        ("/api/superadmin/logs/news", "news.log", "news", structured(action="other")),
        ("/api/superadmin/logs/todo-settlement", "todo_settlement.log", "todo-settlement", structured()),
        ("/api/superadmin/logs/project", "project.log", "project", structured(title="Castle")),
        ("/api/admin/logs/project", "project.log", "project", structured(title="Castle")),
    ],
)
def test_log_endpoints_return_newest_first_without_caching(
    client, endpoint, filename, log_type, line
):
    file_path = Path("logs") / filename
    role = "admin" if endpoint.startswith("/api/admin/") else "superadmin"
    with (
        patch("routes.admin.decorators.verify_jwt_in_request"),
        patch(
            "routes.admin.decorators.get_current_user_from_token",
            return_value=SimpleNamespace(role=role),
        ),
        patch(
            "routes.admin.logs.read_backend_log",
            return_value=(file_path, ["legacy text", line]),
        ) as read_log,
    ):
        response = client.get(f"{endpoint}?limit=2")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    body = response.get_json()
    assert body["type"] == log_type
    assert body["path"] == str(file_path)
    assert body["count"] == 2
    assert body["items"][0]["raw"] == line
    assert body["items"][1]["raw"] == "legacy text"
    read_log.assert_called_once_with(filename, 2)
