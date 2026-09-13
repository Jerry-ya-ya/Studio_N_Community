from uuid import uuid4
from unittest.mock import patch

import pytest
from flask_jwt_extended import create_access_token

from models import User, db


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def profile_accounts(app):
    suffix = uuid4().hex
    with app.app_context():
        user = User(
            username=f"profile-user-{suffix}",
            nickname="Original nickname",
            email=f"profile-user-{suffix}@example.com",
            password="test-password",
            github_url="https://github.com/original",
            avatar_url="https://example.com/avatar.png",
            avatar_source="local",
            role="user",
            review_experience=5,
            pm_experience=9,
            email_verified=True,
        )
        duplicate = User(
            username=f"profile-duplicate-{suffix}",
            email=f"profile-duplicate-{suffix}@example.com",
            password="test-password",
            email_verified=True,
        )
        superadmin = User(
            username=f"profile-superadmin-{suffix}",
            email=f"profile-superadmin-{suffix}@example.com",
            password="test-password",
            role="superadmin",
            email_verified=True,
        )
        db.session.add_all([user, duplicate, superadmin])
        db.session.commit()

        result = {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "token": create_access_token(identity=str(user.id)),
            "duplicate_id": duplicate.id,
            "duplicate_email": duplicate.email,
            "superadmin_id": superadmin.id,
            "superadmin_token": create_access_token(identity=str(superadmin.id)),
        }

    yield result

    with app.app_context():
        User.query.filter(
            User.id.in_([
                result["user_id"],
                result["duplicate_id"],
                result["superadmin_id"],
            ])
        ).delete(synchronize_session=False)
        db.session.commit()


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/me"),
        ("put", "/api/me"),
        ("delete", "/api/me"),
        ("get", "/api/public/1"),
    ],
)
def test_profile_endpoints_require_authentication(client, method, path):
    response = getattr(client, method)(path)

    assert response.status_code == 401


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_me_endpoints_reject_tokens_for_missing_users(app, client, method):
    with app.app_context():
        token = create_access_token(identity="999999999")

    response = getattr(client, method)("/api/me", headers=bearer(token))

    assert response.status_code == 404
    assert response.get_json() == {"error": "User not found"}


def test_get_me_serializes_profile_aliases_and_empty_statistics(
    client, profile_accounts
):
    response = client.get("/api/me", headers=bearer(profile_accounts["token"]))

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["id"] == profile_accounts["user_id"]
    assert payload["username"] == profile_accounts["username"]
    assert payload["email"] == profile_accounts["email"]
    assert payload["nickname"] == "Original nickname"
    assert payload["github_url"] == "https://github.com/original"
    assert payload["githubUrl"] == payload["github_url"]
    assert payload["avatar_url"] == "https://example.com/avatar.png"
    assert payload["avatar_source"] == "local"
    assert payload["avatarSource"] == payload["avatar_source"]
    assert payload["capability_direction"] == payload["capabilityDirection"] == "both"
    assert payload["capability_stack"] == payload["capabilityStack"] == "fullstack"
    assert payload["capability_focus"] == payload["capabilityFocus"] == "game-systems"
    assert payload["capability_style"] == payload["capabilityStyle"] == "professional"
    assert payload["role"] == "user"
    assert payload["pm_experience"] == 9
    assert payload["review_experience"] == 5
    assert payload["created_at"]
    assert payload["coins"] == payload["total_coins"] == payload["totalCoins"] == 0
    assert payload["achievementStats"] == {
        "totalCheckIns": 0,
        "longestCheckInStreak": 0,
        "createdProjects": 0,
        "projectTokensUsed": 0,
        "completedTodos": 0,
        "createdPosts": 0,
        "friends": 0,
    }


def test_update_profile_accepts_snake_case_aliases_and_normalizes_values(
    app, client, profile_accounts
):
    long_github_url = " https://github.com/" + ("a" * 300) + " "

    response = client.put(
        "/api/me",
        headers=bearer(profile_accounts["token"]),
        json={
            "nickname": "Updated nickname",
            "email": f"  {profile_accounts['email']}  ",
            "github_url": long_github_url,
            "avatar_source": "github",
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "message": "Profile updated",
        "email_verification_required": False,
    }
    with app.app_context():
        user = db.session.get(User, profile_accounts["user_id"])
        assert user.nickname == "Updated nickname"
        assert user.github_url == long_github_url.strip()[:255]
        assert user.avatar_source == "github"
        assert user.email == profile_accounts["email"]
        assert user.email_verified is True


def test_update_profile_can_clear_github_url_and_use_camel_case_avatar_source(
    app, client, profile_accounts
):
    response = client.put(
        "/api/me",
        headers=bearer(profile_accounts["token"]),
        json={"githubUrl": "  ", "avatarSource": "local"},
    )

    assert response.status_code == 200
    with app.app_context():
        user = db.session.get(User, profile_accounts["user_id"])
        assert user.github_url is None
        assert user.avatar_source == "local"


def test_update_profile_saves_allowlisted_public_capabilities(
    app, client, profile_accounts
):
    response = client.put(
        "/api/me",
        headers=bearer(profile_accounts["token"]),
        json={
            "capabilityDirection": " independent ",
            "capability_stack": "backend",
            "capabilityFocus": "developer-tools",
            "capability_style": "collaborative",
        },
    )

    assert response.status_code == 200
    with app.app_context():
        user = db.session.get(User, profile_accounts["user_id"])
        assert user.capability_direction == "independent"
        assert user.capability_stack == "backend"
        assert user.capability_focus == "developer-tools"
        assert user.capability_style == "collaborative"

    profile = client.get("/api/me", headers=bearer(profile_accounts["token"])).get_json()
    assert profile["capabilityDirection"] == "independent"
    assert profile["capabilityStack"] == "backend"
    assert profile["capabilityFocus"] == "developer-tools"
    assert profile["capabilityStyle"] == "collaborative"


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("capabilityDirection", "<script>alert(1)</script>", "capabilityDirection is not an allowed option"),
        ("capabilityStack", "a" * 1000, "capabilityStack is not an allowed option"),
        ("capabilityFocus", 42, "capabilityFocus must be a string"),
        ("capabilityStyle", None, "capabilityStyle must be a string"),
    ],
)
def test_update_profile_rejects_unsafe_public_capabilities(
    client, profile_accounts, field, value, error
):
    response = client.put(
        "/api/me",
        headers=bearer(profile_accounts["token"]),
        json={field: value},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": error}


def test_update_profile_rejects_empty_duplicate_and_invalid_values(
    client, profile_accounts
):
    headers = bearer(profile_accounts["token"])

    empty_email = client.put("/api/me", headers=headers, json={"email": "   "})
    duplicate_email = client.put(
        "/api/me",
        headers=headers,
        json={"email": f"  {profile_accounts['duplicate_email']}  "},
    )
    invalid_avatar = client.put(
        "/api/me", headers=headers, json={"avatarSource": "gravatar"}
    )

    assert empty_email.status_code == 400
    assert empty_email.get_json() == {"error": "Email cannot be empty"}
    assert duplicate_email.status_code == 400
    assert duplicate_email.get_json() == {"error": "Email already exists"}
    assert invalid_avatar.status_code == 400
    assert invalid_avatar.get_json() == {
        "error": "Avatar source must be local or github"
    }


def test_update_profile_rejects_non_object_payload(client, profile_accounts):
    response = client.put(
        "/api/me",
        headers=bearer(profile_accounts["token"]),
        json=[{"capabilityStyle": "professional"}],
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Profile payload must be an object"}


def test_update_profile_email_change_invalidates_email_and_sends_verification(
    app, client, monkeypatch, profile_accounts
):
    new_email = f"updated-{uuid4().hex}@example.com"
    monkeypatch.setitem(app.config, "API_URL", "https://api.example.test/")

    with patch("routes.auth.me.mail.send") as send_mail:
        response = client.put(
            "/api/me",
            headers=bearer(profile_accounts["token"]),
            json={"email": f"  {new_email}  "},
        )

    assert response.status_code == 200
    assert response.get_json() == {
        "message": "Profile updated",
        "email_verification_required": True,
    }
    send_mail.assert_called_once()
    message = send_mail.call_args.args[0]
    assert message.subject == "驗證你的新 Email"
    assert message.recipients == [new_email]
    assert message.body.startswith(
        "請點擊連結完成新 Email 驗證：https://api.example.test/api/verify-email/"
    )
    with app.app_context():
        user = db.session.get(User, profile_accounts["user_id"])
        assert user.email == new_email
        assert user.email_verified is False


def test_public_profile_returns_active_and_deleted_display_values(
    app, client, profile_accounts
):
    headers = bearer(profile_accounts["token"])

    active_response = client.get(
        f"/api/public/{profile_accounts['duplicate_id']}", headers=headers
    )

    assert active_response.status_code == 200
    active = active_response.get_json()
    assert active["id"] == profile_accounts["duplicate_id"]
    assert "email" not in active
    assert active["avatar_source"] == active["avatarSource"] == "github"
    assert active["capabilityDirection"] == "both"
    assert active["capabilityStack"] == "fullstack"
    assert active["capabilityFocus"] == "game-systems"
    assert active["capabilityStyle"] == "professional"
    assert active["github_url"] == active["githubUrl"] is None
    assert active["created_at"]
    assert active["pm_experience"] == 0
    assert active["review_experience"] == 0
    assert active["coins"] == 0

    with app.app_context():
        target = db.session.get(User, profile_accounts["duplicate_id"])
        target.is_deleted = True
        db.session.commit()

    deleted_response = client.get(
        f"/api/public/{profile_accounts['duplicate_id']}", headers=headers
    )

    assert deleted_response.status_code == 200
    deleted = deleted_response.get_json()
    assert deleted["username"] == "已刪除"
    assert deleted["nickname"] == "已刪除"
    assert "email" not in deleted


def test_public_profile_only_exposes_email_to_superadmin(client, profile_accounts):
    response = client.get(
        f"/api/public/{profile_accounts['duplicate_id']}",
        headers=bearer(profile_accounts["superadmin_token"]),
    )

    assert response.status_code == 200
    assert response.get_json()["email"] == profile_accounts["duplicate_email"]


def test_public_profile_returns_not_found(client, profile_accounts):
    response = client.get(
        "/api/public/999999999", headers=bearer(profile_accounts["token"])
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "用戶不存在"}


def test_square_serializes_profile_levels_and_coins(client, profile_accounts):
    response = client.get(
        "/api/square", headers=bearer(profile_accounts["token"])
    )

    assert response.status_code == 200
    profile = next(
        item for item in response.get_json()
        if item["id"] == profile_accounts["user_id"]
    )
    assert profile["pm_experience"] == 9
    assert profile["review_experience"] == 5
    assert profile["coins"] == 0


def test_delete_profile_requires_exact_confirmation(client, profile_accounts):
    headers = bearer(profile_accounts["token"])

    missing = client.delete("/api/me", headers=headers)
    wrong_case = client.delete(
        "/api/me", headers=headers, json={"confirmation": "delete"}
    )

    assert missing.status_code == 400
    assert missing.get_json() == {
        "error": "Type DELETE to confirm account deletion"
    }
    assert wrong_case.status_code == 400
    assert wrong_case.get_json() == missing.get_json()


def test_delete_profile_protects_superadmin_accounts(client, profile_accounts):
    response = client.delete(
        "/api/me",
        headers=bearer(profile_accounts["superadmin_token"]),
        json={"confirmation": "DELETE"},
    )

    assert response.status_code == 403
    assert response.get_json() == {
        "error": "Superadmin accounts cannot be deleted from settings"
    }


def test_delete_profile_anonymizes_account_and_revokes_profile_access(
    app, client, profile_accounts
):
    response = client.delete(
        "/api/me",
        headers=bearer(profile_accounts["token"]),
        json={"confirmation": "DELETE"},
    )

    assert response.status_code == 200
    assert response.get_json() == {"message": "Account deleted"}
    refresh_cookie = "\n".join(response.headers.getlist("Set-Cookie"))
    assert "refresh_token_cookie=;" in refresh_cookie
    with app.app_context():
        user = db.session.get(User, profile_accounts["user_id"])
        assert user.is_deleted is True
        assert user.deleted_at is not None
        assert user.email_verified is False
        assert user.username == f"deleted_user_{profile_accounts['user_id']}"
        assert user.nickname == "已刪除"
        assert user.email == (
            f"deleted_user_{profile_accounts['user_id']}@deleted.local"
        )
        assert user.github_url is None
        assert user.avatar_url is None
        assert user.avatar_source == "github"

    rejected = client.get("/api/me", headers=bearer(profile_accounts["token"]))
    assert rejected.status_code == 404
    assert rejected.get_json() == {"error": "User not found"}
