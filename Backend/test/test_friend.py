from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token
from sqlalchemy import or_

from models import FriendRequest, User, db, friend_association


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def friend_accounts(app):
    suffix = uuid4().hex
    with app.app_context():
        alice = User(
            username=f"friend-alice-{suffix}",
            nickname="Alice",
            email=f"friend-alice-{suffix}@example.com",
            password="test-password",
            avatar_url="https://example.com/alice.png",
            avatar_source="upload",
            github_url="https://github.com/alice",
            role="admin",
            review_experience=5,
            pm_experience=9,
            email_verified=True,
        )
        bob = User(
            username=f"friend-bob-{suffix}",
            email=f"friend-bob-{suffix}@example.com",
            password="test-password",
            email_verified=True,
        )
        charlie = User(
            username=f"friend-charlie-{suffix}",
            email=f"friend-charlie-{suffix}@example.com",
            password="test-password",
            email_verified=True,
        )
        db.session.add_all([alice, bob, charlie])
        db.session.commit()

        result = {
            "alice_id": alice.id,
            "alice_username": alice.username,
            "alice_email": alice.email,
            "alice_token": create_access_token(identity=str(alice.id)),
            "bob_id": bob.id,
            "bob_username": bob.username,
            "bob_token": create_access_token(identity=str(bob.id)),
            "charlie_id": charlie.id,
            "charlie_token": create_access_token(identity=str(charlie.id)),
        }

    yield result

    with app.app_context():
        user_ids = [
            result["alice_id"],
            result["bob_id"],
            result["charlie_id"],
        ]
        FriendRequest.query.filter(
            or_(
                FriendRequest.from_user_id.in_(user_ids),
                FriendRequest.to_user_id.in_(user_ids),
            )
        ).delete(synchronize_session=False)
        db.session.execute(
            friend_association.delete().where(
                or_(
                    friend_association.c.user_id.in_(user_ids),
                    friend_association.c.friend_id.in_(user_ids),
                )
            )
        )
        User.query.filter(User.id.in_(user_ids)).delete(synchronize_session=False)
        db.session.commit()


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("delete", "/api/friends/remove/1"),
        ("get", "/api/friends/list"),
        ("post", "/api/friends/request"),
        ("get", "/api/friends/requests"),
        ("post", "/api/friends/accept/1"),
        ("post", "/api/friends/reject/1"),
    ],
)
def test_friend_endpoints_require_authentication(client, method, path):
    response = getattr(client, method)(path)

    assert response.status_code == 401


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("delete", "/api/friends/remove/1"),
        ("get", "/api/friends/list"),
        ("post", "/api/friends/request"),
        ("get", "/api/friends/requests"),
        ("post", "/api/friends/accept/1"),
        ("post", "/api/friends/reject/1"),
    ],
)
def test_friend_endpoints_reject_tokens_for_missing_users(app, client, method, path):
    with app.app_context():
        token = create_access_token(identity="999999999")

    response = getattr(client, method)(path, headers=bearer(token))

    assert response.status_code == 404
    assert response.get_json() == {"error": "User not found"}


def test_send_friend_request_validates_target(client, friend_accounts):
    headers = bearer(friend_accounts["alice_token"])

    missing_username = client.post("/api/friends/request", headers=headers)
    unknown_user = client.post(
        "/api/friends/request",
        headers=headers,
        json={"to_username": "does-not-exist"},
    )
    self_request = client.post(
        "/api/friends/request",
        headers=headers,
        json={"to_username": friend_accounts["alice_username"]},
    )

    assert missing_username.status_code == 400
    assert missing_username.get_json() == {"error": "請填寫使用者名稱"}
    assert unknown_user.status_code == 400
    assert unknown_user.get_json() == {"error": "用戶不存在或無效"}
    assert self_request.status_code == 400
    assert self_request.get_json() == {"error": "用戶不存在或無效"}


def test_send_friend_request_creates_only_one_pending_request(
    app, client, friend_accounts
):
    headers = bearer(friend_accounts["alice_token"])
    payload = {"to_username": friend_accounts["bob_username"]}

    created = client.post("/api/friends/request", headers=headers, json=payload)
    duplicate = client.post("/api/friends/request", headers=headers, json=payload)

    assert created.status_code == 200
    assert created.get_json() == {"message": "邀請已發送"}
    assert duplicate.status_code == 200
    assert duplicate.get_json() == {"message": "已發送邀請"}
    with app.app_context():
        requests = FriendRequest.query.filter_by(
            from_user_id=friend_accounts["alice_id"],
            to_user_id=friend_accounts["bob_id"],
        ).all()
        assert len(requests) == 1


def test_send_friend_request_is_idempotent_for_existing_friends(
    app, client, friend_accounts
):
    with app.app_context():
        alice = db.session.get(User, friend_accounts["alice_id"])
        bob = db.session.get(User, friend_accounts["bob_id"])
        alice.friends.append(bob)
        db.session.commit()

    response = client.post(
        "/api/friends/request",
        headers=bearer(friend_accounts["alice_token"]),
        json={"to_username": friend_accounts["bob_username"]},
    )

    assert response.status_code == 200
    assert response.get_json() == {"message": "你們已是好友"}
    with app.app_context():
        assert FriendRequest.query.filter_by(
            from_user_id=friend_accounts["alice_id"],
            to_user_id=friend_accounts["bob_id"],
        ).count() == 0


def test_get_friend_requests_lists_invitations_for_current_user(
    app, client, friend_accounts
):
    with app.app_context():
        request_for_bob = FriendRequest(
            from_user_id=friend_accounts["alice_id"],
            to_user_id=friend_accounts["bob_id"],
        )
        request_for_someone_else = FriendRequest(
            from_user_id=friend_accounts["alice_id"],
            to_user_id=friend_accounts["charlie_id"],
        )
        db.session.add_all([request_for_bob, request_for_someone_else])
        db.session.commit()
        request_id = request_for_bob.id

    response = client.get(
        "/api/friends/requests",
        headers=bearer(friend_accounts["bob_token"]),
    )

    assert response.status_code == 200
    assert response.get_json() == [
        {
            "id": request_id,
            "from_username": friend_accounts["alice_username"],
        }
    ]


def test_accept_friend_request_rejects_missing_or_foreign_requests(
    app, client, friend_accounts
):
    with app.app_context():
        foreign_request = FriendRequest(
            from_user_id=friend_accounts["alice_id"],
            to_user_id=friend_accounts["bob_id"],
        )
        db.session.add(foreign_request)
        db.session.commit()
        request_id = foreign_request.id

    missing = client.post(
        "/api/friends/accept/999999999",
        headers=bearer(friend_accounts["alice_token"]),
    )
    foreign = client.post(
        f"/api/friends/accept/{request_id}",
        headers=bearer(friend_accounts["charlie_token"]),
    )

    assert missing.status_code == 404
    assert missing.get_json() == {"error": "邀請不存在"}
    assert foreign.status_code == 404
    assert foreign.get_json() == {"error": "邀請不存在"}


def test_accept_friend_request_creates_bidirectional_friendship(
    app, client, friend_accounts
):
    with app.app_context():
        friend_request = FriendRequest(
            from_user_id=friend_accounts["alice_id"],
            to_user_id=friend_accounts["bob_id"],
        )
        db.session.add(friend_request)
        db.session.commit()
        request_id = friend_request.id

    response = client.post(
        f"/api/friends/accept/{request_id}",
        headers=bearer(friend_accounts["bob_token"]),
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "message": f"你與 {friend_accounts['alice_username']} 已成為好友"
    }
    with app.app_context():
        alice = db.session.get(User, friend_accounts["alice_id"])
        bob = db.session.get(User, friend_accounts["bob_id"])
        assert bob in alice.friends
        assert alice in bob.friends
        assert db.session.get(FriendRequest, request_id) is None


def test_accept_friend_request_does_not_duplicate_existing_friendship(
    app, client, friend_accounts
):
    with app.app_context():
        alice = db.session.get(User, friend_accounts["alice_id"])
        bob = db.session.get(User, friend_accounts["bob_id"])
        alice.friends.append(bob)
        bob.friends.append(alice)
        friend_request = FriendRequest(from_user_id=alice.id, to_user_id=bob.id)
        db.session.add(friend_request)
        db.session.commit()
        request_id = friend_request.id

    response = client.post(
        f"/api/friends/accept/{request_id}",
        headers=bearer(friend_accounts["bob_token"]),
    )

    assert response.status_code == 200
    with app.app_context():
        rows = db.session.execute(
            friend_association.select().where(
                or_(
                    (friend_association.c.user_id == friend_accounts["alice_id"])
                    & (friend_association.c.friend_id == friend_accounts["bob_id"]),
                    (friend_association.c.user_id == friend_accounts["bob_id"])
                    & (friend_association.c.friend_id == friend_accounts["alice_id"]),
                )
            )
        ).all()
        assert len(rows) == 2
        assert db.session.get(FriendRequest, request_id) is None


def test_reject_friend_request_rejects_missing_or_foreign_requests(
    app, client, friend_accounts
):
    with app.app_context():
        foreign_request = FriendRequest(
            from_user_id=friend_accounts["alice_id"],
            to_user_id=friend_accounts["bob_id"],
        )
        db.session.add(foreign_request)
        db.session.commit()
        request_id = foreign_request.id

    missing = client.post(
        "/api/friends/reject/999999999",
        headers=bearer(friend_accounts["alice_token"]),
    )
    foreign = client.post(
        f"/api/friends/reject/{request_id}",
        headers=bearer(friend_accounts["charlie_token"]),
    )

    assert missing.status_code == 404
    assert missing.get_json() == {"error": "邀請不存在"}
    assert foreign.status_code == 404
    assert foreign.get_json() == {"error": "邀請不存在"}


def test_reject_friend_request_deletes_invitation(app, client, friend_accounts):
    with app.app_context():
        friend_request = FriendRequest(
            from_user_id=friend_accounts["alice_id"],
            to_user_id=friend_accounts["bob_id"],
        )
        db.session.add(friend_request)
        db.session.commit()
        request_id = friend_request.id

    response = client.post(
        f"/api/friends/reject/{request_id}",
        headers=bearer(friend_accounts["bob_token"]),
    )

    assert response.status_code == 200
    assert response.get_json() == {"message": "已拒絕好友邀請"}
    with app.app_context():
        assert db.session.get(FriendRequest, request_id) is None


def test_get_friends_serializes_profile_fields_and_fallbacks(
    app, client, friend_accounts
):
    with app.app_context():
        alice = db.session.get(User, friend_accounts["alice_id"])
        bob = db.session.get(User, friend_accounts["bob_id"])
        bob.friends.extend([alice])
        db.session.commit()

    response = client.get(
        "/api/friends/list",
        headers=bearer(friend_accounts["bob_token"]),
    )

    assert response.status_code == 200
    assert response.get_json() == [
        {
            "id": friend_accounts["alice_id"],
            "username": friend_accounts["alice_username"],
            "name": "Alice",
            "nickname": "Alice",
            "githubUrl": "https://github.com/alice",
            "avatarUrl": "https://example.com/alice.png",
            "avatarSource": "upload",
            "role": "admin",
            "pm_experience": 9,
            "review_experience": 5,
            "coins": 0,
        }
    ]


def test_remove_friend_handles_missing_user_and_non_friend(
    client, friend_accounts
):
    headers = bearer(friend_accounts["alice_token"])

    missing = client.delete("/api/friends/remove/999999999", headers=headers)
    non_friend = client.delete(
        f"/api/friends/remove/{friend_accounts['bob_id']}", headers=headers
    )

    assert missing.status_code == 404
    assert missing.get_json() == {"error": "找不到用戶"}
    assert non_friend.status_code == 400
    assert non_friend.get_json() == {"error": "此用戶不是你的好友"}


def test_remove_friend_deletes_current_users_friendship(
    app, client, friend_accounts
):
    with app.app_context():
        alice = db.session.get(User, friend_accounts["alice_id"])
        bob = db.session.get(User, friend_accounts["bob_id"])
        alice.friends.append(bob)
        db.session.commit()

    response = client.delete(
        f"/api/friends/remove/{friend_accounts['bob_id']}",
        headers=bearer(friend_accounts["alice_token"]),
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "message": f"已刪除 {friend_accounts['bob_username']} 為好友"
    }
    with app.app_context():
        alice = db.session.get(User, friend_accounts["alice_id"])
        bob = db.session.get(User, friend_accounts["bob_id"])
        assert bob not in alice.friends
