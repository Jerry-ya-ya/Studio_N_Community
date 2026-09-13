from datetime import date
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token

from image_upload import InvalidImageError
from models import DailyCheckIn, HomeNewsItem, User, db
from routes.admin import content


@pytest.fixture()
def content_accounts(app):
    suffix = uuid4().hex
    with app.app_context():
        admin = User(
            username=f"content-admin-{suffix}",
            nickname="Content Admin",
            email=f"content-admin-{suffix}@example.com",
            password="test-password",
            role="admin",
            email_verified=True,
        )
        member = User(
            username=f"content-member-{suffix}",
            nickname="Content Member",
            email=f"content-member-{suffix}@example.com",
            password="test-password",
            role="member",
            github_url="https://github.com/content-member",
            avatar_url="/member.png",
            avatar_source="upload",
            review_experience=5,
            pm_experience=9,
            email_verified=True,
        )
        db.session.add_all([admin, member])
        db.session.flush()
        db.session.add(DailyCheckIn(
            user_id=member.id,
            checkin_date=date(2026, 9, 12),
            points=11,
        ))
        db.session.commit()
        result = {
            "admin_id": admin.id,
            "admin_token": create_access_token(identity=str(admin.id)),
            "member_id": member.id,
            "member_token": create_access_token(identity=str(member.id)),
        }

    yield result

    with app.app_context():
        DailyCheckIn.query.filter(
            DailyCheckIn.user_id.in_([result["admin_id"], result["member_id"]])
        ).delete(synchronize_session=False)
        HomeNewsItem.query.filter(
            HomeNewsItem.title.like("content-%")
        ).delete(synchronize_session=False)
        User.query.filter(
            User.id.in_([result["admin_id"], result["member_id"]])
        ).delete(synchronize_session=False)
        db.session.commit()


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize(
    ("payload", "default_theme", "message"),
    [
        ([], None, "news item must be an object"),
        ({"title": "T", "summary": "S", "tag": "G"}, None, "theme must be cmen or eden"),
        ({"theme": "other", "title": "T", "summary": "S", "tag": "G"}, None, "theme must be cmen or eden"),
        ({"theme": "cmen", "summary": "S", "tag": "G"}, None, "title is required"),
        ({"theme": "cmen", "title": "T", "tag": "G"}, None, "summary is required"),
        ({"theme": "cmen", "title": "T", "summary": "S"}, None, "tag is required"),
        ({"theme": "cmen", "title": "T", "summary": "S", "tag": "G", "sort_order": []}, None, "sort_order must be a number"),
    ],
)
def test_read_item_payload_validation(payload, default_theme, message):
    parsed, error = content.read_item_payload(payload, default_theme=default_theme)

    assert parsed is None
    assert error == (message, 400)


def test_read_item_payload_normalizes_aliases_defaults_and_lengths():
    parsed, error = content.read_item_payload(
        {
            "title": f"  {'T' * 130}  ",
            "summary": "  Summary  ",
            "tag": f"  {'G' * 50}  ",
            "background_url": f"/{'b' * 300}",
        },
        default_theme="eden",
        default_order=7,
    )

    assert error is None
    assert parsed == {
        "theme": "eden",
        "title": "T" * 120,
        "summary": "Summary",
        "tag": "G" * 40,
        "background_url": f"/{'b' * 254}",
        "sort_order": 7,
    }


def test_default_serializers_and_grouped_news_fallback(app):
    defaults = content.serialize_defaults()
    members = content.serialize_member_defaults()

    assert set(defaults) == {"cmen", "eden"}
    assert len(defaults["cmen"]) == len(defaults["eden"]) == 3
    assert defaults["cmen"][0]["id"] is None
    assert [item["sort_order"] for item in defaults["eden"]] == [0, 1, 2]
    assert len(members) == 12
    assert members[0]["githubUrl"] == "https://github.com/Jerry-ya-ya"

    with patch.object(content.HomeNewsItem, "query") as query:
        query.order_by.return_value.all.return_value = []
        assert content.grouped_home_news() == defaults


def test_content_logging_helpers_include_actor_ip_and_news_copy(app):
    actor = SimpleNamespace(
        id=8,
        display_username="admin",
        display_nickname="Boss",
        role="superadmin",
    )
    with (
        app.test_request_context(
            "/", headers={"X-Forwarded-For": "203.0.113.7, 10.0.0.1"}
        ),
        patch.object(content, "get_current_user_from_token", return_value=actor),
        patch.object(content, "write_content_log") as content_log,
        patch.object(content, "write_news_log") as news_log,
    ):
        content.log_content_event(
            "info", "create_home_news_item", "success", item_id=4
        )

    payload = content_log.call_args.kwargs
    assert payload["admin_id"] == 8
    assert payload["username"] == "admin"
    assert payload["nickname"] == "Boss"
    assert payload["ip"] == "203.0.113.7"
    assert news_log.call_args.kwargs == payload

    with patch.object(content, "get_current_user_from_token", return_value=None):
        assert content.admin_actor_payload() == {
            "admin_id": None,
            "username": "Admin",
            "nickname": "-",
            "role": "-",
        }

    logger = SimpleNamespace(info=Mock())
    with (
        patch.object(content, "content_logger", logger),
        patch.object(content, "news_logger", logger),
    ):
        content.write_content_log("unknown", action="test")
        content.write_news_log("unknown", action="test")
    assert logger.info.call_count == 2


def test_public_and_admin_member_lists(client, content_accounts):
    public = client.get("/api/content/members")
    assert public.status_code == 200
    member = next(
        item for item in public.get_json() if item["id"] == content_accounts["member_id"]
    )
    assert member["name"] == "Content Member"
    assert member["role"] == "member"
    assert member["githubUrl"] == "https://github.com/content-member"
    assert member["avatarUrl"] == "/member.png"
    assert member["avatarSource"] == "upload"
    assert member["pm_experience"] == 9
    assert member["review_experience"] == 5
    assert member["coins"] == 11

    admin = client.get(
        "/api/admin/content/members",
        headers=bearer(content_accounts["admin_token"]),
    )
    assert admin.status_code == 200
    assert content_accounts["member_id"] in [item["id"] for item in admin.get_json()]

    readonly = client.put(
        "/api/admin/content/members",
        headers=bearer(content_accounts["admin_token"]),
        json=[],
    )
    assert readonly.status_code == 405
    assert "cannot be edited" in readonly.get_json()["error"]


def test_public_members_returns_defaults_when_no_registered_members(client):
    with patch("routes.admin.content.list_registered_members", return_value=[]):
        response = client.get("/api/content/members")

    assert response.status_code == 200
    assert response.get_json() == content.serialize_member_defaults()


def test_content_admin_endpoints_require_admin(client, content_accounts):
    assert client.get("/api/admin/content/home-news").status_code == 401
    response = client.get(
        "/api/admin/content/home-news",
        headers=bearer(content_accounts["member_token"]),
    )
    assert response.status_code == 403
    assert response.get_json() == {"error": "需要管理員權限"}


def test_home_news_crud_and_public_grouping(client, app, content_accounts):
    suffix = uuid4().hex
    headers = bearer(content_accounts["admin_token"])
    created = client.post(
        "/api/admin/content/home-news/items",
        headers=headers,
        json={
            "theme": "cmen",
            "title": f"content-{suffix}-created",
            "summary": "Original",
            "tag": "Studio",
            "backgroundUrl": "/old.png",
            "sort_order": "3",
        },
    )
    assert created.status_code == 201
    item_id = created.get_json()["id"]
    assert created.get_json()["backgroundUrl"] == "/old.png"

    updated = client.put(
        f"/api/admin/content/home-news/items/{item_id}",
        headers=headers,
        json={
            "theme": "eden",
            "title": f"content-{suffix}-updated",
            "summary": "Updated",
            "tag": "Network",
            "sort_order": 1,
        },
    )
    assert updated.status_code == 200
    assert updated.get_json()["theme"] == "eden"
    assert updated.get_json()["sort_order"] == 1

    public = client.get("/api/content/home-news")
    assert public.status_code == 200
    assert item_id in [item["id"] for item in public.get_json()["eden"]]
    admin = client.get("/api/admin/content/home-news", headers=headers)
    assert admin.status_code == 200

    deleted = client.delete(
        f"/api/admin/content/home-news/items/{item_id}", headers=headers
    )
    assert deleted.status_code == 200
    assert deleted.get_json() == {"message": "home news item deleted", "id": item_id}
    with app.app_context():
        assert db.session.get(HomeNewsItem, item_id) is None


@pytest.mark.parametrize(
    ("method", "path", "payload", "message"),
    [
        ("post", "/api/admin/content/home-news/items", {}, "theme must be cmen or eden"),
        ("post", "/api/admin/content/home-news/items", {"theme": "cmen"}, "title is required"),
    ],
)
def test_create_home_news_validation_errors(
    client, content_accounts, method, path, payload, message
):
    response = getattr(client, method)(
        path, headers=bearer(content_accounts["admin_token"]), json=payload
    )
    assert response.status_code == 400
    assert response.get_json() == {"error": message}


def test_update_home_news_validation_and_missing_items(client, app, content_accounts):
    suffix = uuid4().hex
    with app.app_context():
        item = HomeNewsItem(
            theme="cmen",
            title=f"content-{suffix}-validation",
            summary="Summary",
            tag="Tag",
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    headers = bearer(content_accounts["admin_token"])
    response = client.put(
        f"/api/admin/content/home-news/items/{item_id}",
        headers=headers,
        json={"title": "", "summary": "Summary", "tag": "Tag"},
    )
    assert response.status_code == 400
    assert response.get_json() == {"error": "title is required"}
    assert client.put(
        "/api/admin/content/home-news/items/999999", headers=headers, json={}
    ).status_code == 404
    assert client.delete(
        "/api/admin/content/home-news/items/999999", headers=headers
    ).status_code == 404


def test_replace_home_news_validation_and_success(client, app, content_accounts):
    suffix = uuid4().hex
    headers = bearer(content_accounts["admin_token"])
    bad_collection = client.put(
        "/api/admin/content/home-news", headers=headers, json={"cmen": {}}
    )
    assert bad_collection.status_code == 400
    assert bad_collection.get_json() == {"error": "cmen must be a list"}

    bad_item = client.put(
        "/api/admin/content/home-news",
        headers=headers,
        json={"cmen": [{}], "eden": []},
    )
    assert bad_item.status_code == 400
    assert bad_item.get_json() == {"error": "title is required"}

    response = client.put(
        "/api/admin/content/home-news",
        headers=headers,
        json={
            "cmen": [
                {
                    "title": f"content-{suffix}-cmen",
                    "summary": "Cmen summary",
                    "tag": "Studio",
                }
            ],
            "eden": [
                {
                    "title": f"content-{suffix}-eden",
                    "summary": "Eden summary",
                    "tag": "Network",
                    "sort_order": 5,
                }
            ],
        },
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["cmen"][0]["sort_order"] == 0
    assert body["eden"][0]["sort_order"] == 5

    with app.app_context():
        HomeNewsItem.query.delete()
        db.session.commit()


def test_home_news_background_upload_errors_and_success(
    client, app, content_accounts
):
    suffix = uuid4().hex
    with app.app_context():
        item = HomeNewsItem(
            theme="cmen",
            title=f"content-{suffix}-image",
            summary="Summary",
            tag="Tag",
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    endpoint = f"/api/admin/content/home-news/items/{item_id}/background"
    headers = bearer(content_accounts["admin_token"])
    response = client.post(endpoint, headers=headers)
    assert response.status_code == 400
    assert response.get_json() == {"error": "No file part"}

    with patch(
        "routes.admin.content.request",
        SimpleNamespace(
            files={"file": SimpleNamespace(filename="")},
            headers={},
            remote_addr="127.0.0.1",
        ),
    ):
        response = client.post(endpoint, headers=headers)
    assert response.status_code == 400
    assert response.get_json() == {"error": "No selected file"}

    with patch(
        "routes.admin.content.save_validated_image",
        side_effect=InvalidImageError("invalid image"),
    ):
        response = client.post(
            endpoint,
            headers=headers,
            data={"image": (BytesIO(b"bad"), "bad.png")},
            content_type="multipart/form-data",
        )
    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid image", "code": "invalid_image"}

    with patch(
        "routes.admin.content.save_validated_image",
        return_value="safe.png",
    ) as save_image:
        response = client.post(
            endpoint,
            headers=headers,
            data={"background": (BytesIO(b"png"), "source.png")},
            content_type="multipart/form-data",
        )
    assert response.status_code == 200
    assert response.get_json()["backgroundUrl"] == "/static/uploads/home-news/safe.png"
    uploaded, folder, prefix = save_image.call_args.args
    assert uploaded.filename == "source.png"
    assert folder.replace("\\", "/").endswith("static/uploads/home-news")
    assert prefix == f"home-news-{item_id}"
