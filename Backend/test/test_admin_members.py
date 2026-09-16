from datetime import date
from unittest.mock import patch
from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token

from models import DailyCheckIn, User, db
from role_groups import Permission, Role, assignable_role_names, has_permission


@pytest.fixture()
def management_accounts(app):
    suffix = uuid4().hex
    with app.app_context():
        superadmin = User(
            username=f"manage-super-{suffix}",
            email=f"manage-super-{suffix}@example.com",
            password="test-password",
            role="superadmin",
            email_verified=True,
        )
        admin = User(
            username=f"manage-admin-{suffix}",
            email=f"manage-admin-{suffix}@example.com",
            password="test-password",
            role="admin",
            email_verified=True,
            experience=17,
            review_experience=5,
            pm_experience=9,
        )
        member = User(
            username=f"manage-member-{suffix}",
            email=f"manage-member-{suffix}@example.com",
            password="test-password",
            role="user",
            email_verified=True,
        )
        db.session.add_all([superadmin, admin, member])
        db.session.flush()
        db.session.add_all(
            [
                DailyCheckIn(
                    user_id=admin.id,
                    checkin_date=date(2026, 9, 9),
                    points=4,
                ),
                DailyCheckIn(
                    user_id=admin.id,
                    checkin_date=date(2026, 9, 10),
                    points=6,
                ),
            ]
        )
        db.session.commit()
        result = {
            "super_id": superadmin.id,
            "super_token": create_access_token(identity=str(superadmin.id)),
            "admin_id": admin.id,
            "admin_token": create_access_token(identity=str(admin.id)),
            "member_id": member.id,
            "member_token": create_access_token(identity=str(member.id)),
            "member_username": member.username,
        }

    yield result

    with app.app_context():
        DailyCheckIn.query.filter(
            DailyCheckIn.user_id.in_(
                [result["super_id"], result["admin_id"], result["member_id"]]
            )
        ).delete(synchronize_session=False)
        User.query.filter(
            User.id.in_(
                [result["super_id"], result["admin_id"], result["member_id"]]
            )
        ).delete(synchronize_session=False)
        db.session.commit()


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_management_endpoints_require_superadmin(client, management_accounts):
    assert client.get("/api/superadmin/promote").status_code == 401
    response = client.get(
        "/api/superadmin/promote",
        headers=bearer(management_accounts["admin_token"]),
    )
    assert response.status_code == 403
    assert response.get_json() == {"error": "需要最高管理員權限"}


def test_account_role_groups_share_one_permission_registry():
    assert assignable_role_names() == [Role.USER.value, Role.ADMIN.value]
    assert not has_permission(Role.USER, Permission.ADMIN_ACCESS)
    assert has_permission(Role.ADMIN, Permission.ADMIN_ACCESS)
    assert has_permission(Role.SUPERADMIN, Permission.ADMIN_ACCESS)
    assert has_permission(Role.SUPERADMIN, Permission.MANAGE_ROLES)
    assert not has_permission('unknown-role', Permission.ADMIN_ACCESS)


def test_role_group_endpoint_exposes_authorization_metadata(
    client, management_accounts
):
    endpoint = "/api/superadmin/role-groups"
    assert client.get(endpoint).status_code == 401
    assert client.get(
        endpoint,
        headers=bearer(management_accounts["admin_token"]),
    ).status_code == 403

    response = client.get(
        endpoint,
        headers=bearer(management_accounts["super_token"]),
    )
    assert response.status_code == 200
    groups = {group["name"]: group for group in response.get_json()}
    assert set(groups) == {"user", "admin", "superadmin"}
    assert groups["user"]["permissions"] == []
    assert groups["admin"]["permissions"] == ["admin.access"]
    assert groups["superadmin"]["assignable"] is False


def test_generic_role_assignment_validates_and_updates_groups(
    client, app, management_accounts
):
    endpoint = f"/api/superadmin/users/{management_accounts['member_id']}/role"
    headers = bearer(management_accounts["super_token"])

    missing_role = client.put(endpoint, headers=headers, json={})
    assert missing_role.status_code == 400
    assert missing_role.get_json()["allowed_roles"] == ["user", "admin"]

    invalid_role = client.put(endpoint, headers=headers, json={"role": "editor"})
    assert invalid_role.status_code == 400
    assert invalid_role.get_json()["error"] == "無效的身分群組"

    protected_role = client.put(
        endpoint,
        headers=headers,
        json={"role": "superadmin"},
    )
    assert protected_role.status_code == 400

    updated = client.put(endpoint, headers=headers, json={"role": " ADMIN "})
    assert updated.status_code == 200
    assert updated.get_json()["user"]["role"] == "admin"
    with app.app_context():
        assert db.session.get(User, management_accounts["member_id"]).role == "admin"

    unchanged = client.put(endpoint, headers=headers, json={"role": "admin"})
    assert unchanged.status_code == 200
    assert unchanged.get_json()["message"] == "身分群組未變更"


@pytest.mark.parametrize(
    "query",
    [
        "?sort_by=username&order=asc",
        "?sort_by=created_at&order=desc",
        "?sort_by=role&order=asc",
        "?sort_by=unknown&order=desc",
    ],
)
def test_get_users_supports_sorting_and_coin_aliases(
    client, management_accounts, query
):
    response = client.get(
        f"/api/superadmin/promote{query}",
        headers=bearer(management_accounts["super_token"]),
    )
    assert response.status_code == 200
    body = response.get_json()
    admin = next(
        item for item in body if item["id"] == management_accounts["admin_id"]
    )
    assert admin["total_points"] == 10
    assert admin["totalPoints"] == 10
    assert admin["coins"] == admin["total_coins"] == admin["totalCoins"] == 10
    assert admin["experience"] == 17
    assert admin["pm_level"] == 1
    assert admin["review_level"] == 1
    assert admin["review_experience"] == 5
    assert admin["pm_experience"] == 9
    member = next(
        item for item in body if item["id"] == management_accounts["member_id"]
    )
    assert "email" in member
    assert "email_verified" in member
    assert member["total_points"] == 0


def test_promote_user_missing_success_and_already_admin(
    client, app, management_accounts
):
    headers = bearer(management_accounts["super_token"])
    missing = client.put("/api/superadmin/promote/999999", headers=headers)
    assert missing.status_code == 404
    assert missing.get_json() == {"error": "用戶不存在"}

    promoted = client.put(
        f"/api/superadmin/promote/{management_accounts['member_id']}", headers=headers
    )
    assert promoted.status_code == 200
    assert management_accounts["member_username"] in promoted.get_json()["message"]
    with app.app_context():
        assert db.session.get(User, management_accounts["member_id"]).role == "admin"

    repeated = client.put(
        f"/api/superadmin/promote/{management_accounts['member_id']}", headers=headers
    )
    assert repeated.status_code == 200
    assert repeated.get_json() == {"message": "該用戶已是管理員"}


def test_demote_user_handles_all_branches(client, app, management_accounts):
    headers = bearer(management_accounts["super_token"])

    missing = client.put("/api/superadmin/demote/999999", headers=headers)
    assert missing.status_code == 404
    assert missing.get_json() == {"error": "用戶不存在"}

    self_response = client.put(
        f"/api/superadmin/demote/{management_accounts['super_id']}", headers=headers
    )
    assert self_response.status_code == 400
    assert self_response.get_json() == {"error": "不能降級自己"}

    not_admin = client.put(
        f"/api/superadmin/demote/{management_accounts['member_id']}", headers=headers
    )
    assert not_admin.status_code == 200
    assert not_admin.get_json() == {"message": "該用戶不是管理員"}

    demoted = client.put(
        f"/api/superadmin/demote/{management_accounts['admin_id']}", headers=headers
    )
    assert demoted.status_code == 200
    with app.app_context():
        assert db.session.get(User, management_accounts["admin_id"]).role == "user"


def test_demote_returns_unauthorized_when_token_user_disappears(
    client, management_accounts
):
    with patch("routes.admin.promote.get_current_user_from_token", return_value=None):
        response = client.put(
            f"/api/superadmin/demote/{management_accounts['admin_id']}",
            headers=bearer(management_accounts["super_token"]),
        )
    assert response.status_code == 401
    assert response.get_json() == {"error": "使用者不存在"}
