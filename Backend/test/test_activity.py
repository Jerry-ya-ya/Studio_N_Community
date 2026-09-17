from datetime import datetime, timedelta
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token

from models import ActivityPromotion, User, db
from routes.admin.activity import (
    matches_activity_target,
    read_activity_datetime,
    read_activity_payload,
    serialize_activity,
)
from image_upload import InvalidImageError


@pytest.fixture()
def activity_accounts(app):
    suffix = uuid4().hex
    with app.app_context():
        admin = User(
            username=f"activity-admin-{suffix}",
            email=f"activity-admin-{suffix}@example.com",
            password="test-password",
            role="admin",
            email_verified=True,
        )
        member = User(
            username=f"activity-member-{suffix}",
            email=f"activity-member-{suffix}@example.com",
            password="test-password",
            role="user",
            email_verified=True,
        )
        db.session.add_all([admin, member])
        db.session.commit()
        result = {
            "admin_id": admin.id,
            "admin_username": admin.username,
            "admin_token": create_access_token(identity=str(admin.id)),
            "member_id": member.id,
            "member_username": member.username,
            "member_token": create_access_token(identity=str(member.id)),
        }

    yield result

    with app.app_context():
        ActivityPromotion.query.filter(
            ActivityPromotion.created_by_id.in_(
                [result["admin_id"], result["member_id"]]
            )
        ).delete(synchronize_session=False)
        User.query.filter(
            User.id.in_([result["admin_id"], result["member_id"]])
        ).delete(synchronize_session=False)
        db.session.commit()


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize(
    ("target_filter", "role", "username", "expected"),
    [
        (None, "user", "jack", True),
        ("", "user", "jack", True),
        ("*", "user", "jack", True),
        (" role: member ", "member", "jack", True),
        ("role:admin", "member", "jack", False),
        (" user: JACK ", "member", "jack", True),
        ("user:jill", "member", "jack", False),
        ("MEMBER", "member", "jack", True),
        ("JaCk", "member", "jack", True),
        ("nobody", "member", "jack", False),
        ("nobody", "admin", "jack", True),
        ("nobody", "SUPERADMIN", "jack", True),
    ],
)
def test_matches_activity_target_supports_roles_users_and_admin_override(
    target_filter, role, username, expected
):
    activity = SimpleNamespace(target_filter=target_filter)
    user = SimpleNamespace(role=role, username=username)

    assert matches_activity_target(activity, user) is expected


@pytest.mark.parametrize(
    ("value", "expected", "has_error"),
    [
        (None, None, False),
        (123, None, True),
        ("not-a-date", None, True),
        ("2026-09-10T12:30:00", datetime(2026, 9, 10, 12, 30), False),
        ("2026-09-10T12:30:00Z", datetime(2026, 9, 10, 12, 30), False),
    ],
)
def test_read_activity_datetime_accepts_iso_values(value, expected, has_error):
    parsed, error = read_activity_datetime(value)

    assert parsed == expected
    assert bool(error) is has_error


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ([], "activity must be an object"),
        ({"description": "Details"}, "title is required"),
        ({"title": "Title"}, "description is required"),
        (
            {"title": "Title", "description": "Details", "visibility": "friends"},
            "visibility must be public or private",
        ),
        (
            {"title": "Title", "description": "Details", "startAt": "bad"},
            "startAt must be an ISO datetime",
        ),
        (
            {"title": "Title", "description": "Details", "endAt": 123},
            "endAt must be an ISO datetime",
        ),
        (
            {
                "title": "Title",
                "description": "Details",
                "startAt": "2026-09-11T00:00:00",
                "endAt": "2026-09-10T00:00:00",
            },
            "endAt must be after startAt",
        ),
        (
            {"title": "Title", "description": "Details", "sort_order": "first"},
            "sort_order must be a number",
        ),
    ],
)
def test_read_activity_payload_rejects_invalid_input(payload, message):
    result, error = read_activity_payload(payload)

    assert result is None
    assert error == (message, 400)


def test_read_activity_payload_normalizes_aliases_defaults_and_lengths():
    payload, error = read_activity_payload(
        {
            "title": f"  {'T' * 130}  ",
            "description": "  Details  ",
            "target_filter": "member",
            "image_url": f"/{'i' * 300}",
            "start_at": "2026-09-10T08:00:00+08:00",
            "end_at": "2026-09-10T09:00:00+08:00",
        },
        default_order=7,
    )

    assert error is None
    assert payload == {
        "title": "T" * 120,
        "description": "Details",
        "visibility": "private",
        "target_filter": "member",
        "image_url": f"/{'i' * 254}",
        "start_at": datetime(2026, 9, 10, 8),
        "end_at": datetime(2026, 9, 10, 9),
        "sort_order": 7,
    }


def test_serialize_activity_reports_creator_aliases_and_end_state():
    now = datetime(2026, 9, 10, 12)
    activity = SimpleNamespace(
        id=9,
        title="Climb the beanstalk",
        description="An event",
        visibility="public",
        target_filter="all",
        image_url="/activity.png",
        start_at=now - timedelta(hours=2),
        end_at=now - timedelta(hours=1),
        sort_order=3,
        created_by=SimpleNamespace(display_username="Jack"),
        created_by_id=4,
        created_at=now - timedelta(days=1),
        updated_at=now,
    )

    with patch("routes.admin.activity.taipei_now", return_value=now):
        result = serialize_activity(activity)

    assert result["status"] == "ended"
    assert result["isEnded"] is result["is_ended"] is True
    assert result["createdBy"] == "Jack"
    assert result["targetFilter"] == result["target_filter"] == "all"
    assert result["imageUrl"] == result["image_url"] == "/activity.png"
    assert result["startAt"] == result["start_at"]
    assert result["endAt"] == result["end_at"]

    activity.created_by = None
    activity.end_at = None
    result = serialize_activity(activity)
    assert result["status"] == "active"
    assert result["createdBy"] is None
    assert result["endAt"] is None


def test_activity_crud_and_admin_listing(client, app, activity_accounts):
    headers = bearer(activity_accounts["admin_token"])
    create_response = client.post(
        "/api/admin/activities",
        headers=headers,
        json={
            "title": "  CRUD activity  ",
            "description": "  Original details  ",
            "visibility": "public",
            "targetFilter": "all",
            "imageUrl": "/initial.png",
            "startAt": "2026-09-10T08:00:00+08:00",
            "endAt": "2026-09-10T10:00:00+08:00",
            "sort_order": "4",
        },
    )

    assert create_response.status_code == 201
    created = create_response.get_json()
    activity_id = created["id"]
    assert created["title"] == "CRUD activity"
    assert created["createdBy"] == activity_accounts["admin_username"]
    assert created["created_by_id"] == activity_accounts["admin_id"]
    assert created["sort_order"] == 4

    update_response = client.put(
        f"/api/admin/activities/{activity_id}",
        headers=headers,
        json={
            "title": "Updated activity",
            "description": "Updated details",
            "visibility": "private",
            "target_filter": f"user:{activity_accounts['member_username']}",
        },
    )
    assert update_response.status_code == 200
    updated = update_response.get_json()
    assert updated["title"] == "Updated activity"
    assert updated["visibility"] == "private"
    assert updated["sort_order"] == 4
    assert updated["imageUrl"] is None

    list_response = client.get("/api/admin/activities", headers=headers)
    assert list_response.status_code == 200
    assert activity_id in [item["id"] for item in list_response.get_json()]

    delete_response = client.delete(
        f"/api/admin/activities/{activity_id}", headers=headers
    )
    assert delete_response.status_code == 200
    assert delete_response.get_json() == {
        "message": "activity deleted",
        "id": activity_id,
    }
    with app.app_context():
        assert db.session.get(ActivityPromotion, activity_id) is None


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({}, "title is required"),
        (
            {"title": "Invalid", "description": "Details", "sort_order": []},
            "sort_order must be a number",
        ),
    ],
)
def test_create_activity_returns_payload_validation_errors(
    client, activity_accounts, payload, message
):
    response = client.post(
        "/api/admin/activities",
        headers=bearer(activity_accounts["admin_token"]),
        json=payload,
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": message}


def test_update_activity_returns_payload_validation_error(
    client, app, activity_accounts
):
    with app.app_context():
        activity = ActivityPromotion(
            title="Update validation",
            description="Details",
            visibility="private",
            created_by_id=activity_accounts["admin_id"],
        )
        db.session.add(activity)
        db.session.commit()
        activity_id = activity.id

    response = client.put(
        f"/api/admin/activities/{activity_id}",
        headers=bearer(activity_accounts["admin_token"]),
        json={"title": "", "description": "Details"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "title is required"}


def test_public_and_private_activity_feeds_filter_and_sort(
    client, app, activity_accounts
):
    prefix = f"feed-{uuid4().hex}"
    now = datetime.now()
    activities = [
        ActivityPromotion(
            title=f"{prefix}-public-later",
            description="Public",
            visibility="public",
            target_filter="all",
            sort_order=2,
            created_by_id=activity_accounts["admin_id"],
        ),
        ActivityPromotion(
            title=f"{prefix}-public-first",
            description="Public",
            visibility="public",
            target_filter="all",
            sort_order=1,
            end_at=now - timedelta(minutes=1),
            created_by_id=activity_accounts["admin_id"],
        ),
        ActivityPromotion(
            title=f"{prefix}-all",
            description="Private",
            visibility="private",
            target_filter="all",
            created_by_id=activity_accounts["admin_id"],
        ),
        ActivityPromotion(
            title=f"{prefix}-role",
            description="Private",
            visibility="private",
            target_filter="role:user",
            created_by_id=activity_accounts["admin_id"],
        ),
        ActivityPromotion(
            title=f"{prefix}-user",
            description="Private",
            visibility="private",
            target_filter=f"user:{activity_accounts['member_username'].upper()}",
            created_by_id=activity_accounts["admin_id"],
        ),
        ActivityPromotion(
            title=f"{prefix}-hidden",
            description="Private",
            visibility="private",
            target_filter="role:superadmin",
            created_by_id=activity_accounts["admin_id"],
        ),
    ]
    with app.app_context():
        db.session.add_all(activities)
        db.session.commit()

    public_response = client.get("/api/activities")
    assert public_response.status_code == 200
    assert public_response.headers["Cache-Control"] == "no-store"
    public = [
        item for item in public_response.get_json() if item["title"].startswith(prefix)
    ]
    assert [item["title"] for item in public] == [
        f"{prefix}-public-first",
        f"{prefix}-public-later",
    ]
    assert public[0]["status"] == "ended"

    private_response = client.get(
        "/api/private/activities",
        headers=bearer(activity_accounts["member_token"]),
    )
    assert private_response.status_code == 200
    assert private_response.headers["Cache-Control"] == "no-store"
    private_titles = {
        item["title"]
        for item in private_response.get_json()
        if item["title"].startswith(prefix)
    }
    assert private_titles == {
        f"{prefix}-all",
        f"{prefix}-role",
        f"{prefix}-user",
    }


def test_private_feed_handles_missing_user(client, activity_accounts):
    with patch("routes.admin.activity.get_current_user_from_token", return_value=None):
        response = client.get(
            "/api/private/activities",
            headers=bearer(activity_accounts["member_token"]),
        )

    assert response.status_code == 401
    assert response.get_json() == {"error": "使用者不存在"}


def test_activity_admin_endpoints_require_an_admin(client, activity_accounts):
    assert client.get("/api/admin/activities").status_code == 401
    response = client.get(
        "/api/admin/activities",
        headers=bearer(activity_accounts["member_token"]),
    )
    assert response.status_code == 403
    assert response.get_json() == {"error": "需要管理員權限"}


def test_activity_image_upload_errors_success_and_clear(
    client, app, activity_accounts
):
    with app.app_context():
        activity = ActivityPromotion(
            title="Image activity",
            description="Details",
            visibility="private",
            created_by_id=activity_accounts["admin_id"],
        )
        db.session.add(activity)
        db.session.commit()
        activity_id = activity.id

    endpoint = f"/api/admin/activities/{activity_id}/image"
    headers = bearer(activity_accounts["admin_token"])

    response = client.post(endpoint, headers=headers)
    assert response.status_code == 400
    assert response.get_json() == {"error": "No file part"}

    empty_upload = SimpleNamespace(filename="")
    with patch(
        "routes.admin.activity.request",
        SimpleNamespace(files={"file": empty_upload}),
    ):
        response = client.post(endpoint, headers=headers)
    assert response.status_code == 400
    assert response.get_json() == {"error": "No selected file"}

    with patch(
        "routes.admin.activity.upload_validated_image",
        side_effect=InvalidImageError("檔案不是有效的圖片"),
    ):
        response = client.post(
            endpoint,
            headers=headers,
            data={"image": (BytesIO(b"not-an-image"), "fake.png")},
            content_type="multipart/form-data",
        )
    assert response.status_code == 400
    assert response.get_json() == {
        "error": "檔案不是有效的圖片",
        "code": "invalid_image",
    }

    with patch(
        "routes.admin.activity.upload_validated_image",
        return_value=SimpleNamespace(
            blob_name=f"activities/activity-{activity_id}/safe.png",
            url=f"https://example.blob.core.windows.net/media/activities/activity-{activity_id}/safe.png",
        ),
    ) as save_image:
        response = client.post(
            endpoint,
            headers=headers,
            data={"background": (BytesIO(b"png"), "source.png")},
            content_type="multipart/form-data",
        )
    assert response.status_code == 200
    assert response.get_json()["imageUrl"] == (
        f"https://example.blob.core.windows.net/media/activities/activity-{activity_id}/safe.png"
    )
    uploaded_file, filename_prefix = save_image.call_args.args
    assert uploaded_file.filename == "source.png"
    assert filename_prefix == f"activities/activity-{activity_id}"

    response = client.delete(endpoint, headers=headers)
    assert response.status_code == 200
    assert response.get_json()["imageUrl"] is None
    with app.app_context():
        assert db.session.get(ActivityPromotion, activity_id).image_url is None
