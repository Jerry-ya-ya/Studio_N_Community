from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token

from models import Post, PostLike, User, db
from routes.post.post import POST_CONTENT_MAX_LENGTH


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def post_accounts(app):
    suffix = uuid4().hex
    with app.app_context():
        owner = User(
            username=f"post-owner-{suffix}",
            nickname="Post Owner",
            email=f"post-owner-{suffix}@example.com",
            password="test-password",
            avatar_url="https://example.com/owner.png",
            role="user",
            email_verified=True,
        )
        reader = User(
            username=f"post-reader-{suffix}",
            nickname="Post Reader",
            email=f"post-reader-{suffix}@example.com",
            password="test-password",
            role="admin",
            email_verified=True,
        )
        db.session.add_all([owner, reader])
        db.session.commit()

        result = {
            "owner_id": owner.id,
            "reader_id": reader.id,
            "owner_token": create_access_token(identity=str(owner.id)),
            "reader_token": create_access_token(identity=str(reader.id)),
        }

    yield result

    with app.app_context():
        user_ids = [result["owner_id"], result["reader_id"]]
        post_ids = [
            row[0]
            for row in db.session.query(Post.id).filter(Post.user_id.in_(user_ids)).all()
        ]
        if post_ids:
            PostLike.query.filter(PostLike.post_id.in_(post_ids)).delete(
                synchronize_session=False
            )
            Post.query.filter(Post.id.in_(post_ids)).delete(synchronize_session=False)
        PostLike.query.filter(PostLike.user_id.in_(user_ids)).delete(
            synchronize_session=False
        )
        User.query.filter(User.id.in_(user_ids)).delete(synchronize_session=False)
        db.session.commit()


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/api/post"),
        ("get", "/api/post"),
        ("get", "/api/post/me"),
        ("post", "/api/post/1/like"),
        ("put", "/api/post/1"),
        ("delete", "/api/post/1"),
    ],
)
def test_post_endpoints_require_authentication(client, method, path):
    kwargs = {"json": {}} if method in {"post", "put"} else {}
    response = getattr(client, method)(path, **kwargs)

    assert response.status_code == 401


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/api/post"),
        ("get", "/api/post"),
        ("get", "/api/post/me"),
        ("post", "/api/post/1/like"),
        ("put", "/api/post/1"),
        ("delete", "/api/post/1"),
    ],
)
def test_post_endpoints_reject_tokens_for_missing_users(app, client, method, path):
    with app.app_context():
        token = create_access_token(identity="999999999")

    kwargs = {"json": {"content": "unused"}} if method in {"post", "put"} else {}
    response = getattr(client, method)(path, headers=bearer(token), **kwargs)

    assert response.status_code == 404
    assert response.get_json() == {"error": "User not found"}


@pytest.mark.parametrize("payload", [{}, None, {"content": "   "}])
def test_create_post_rejects_empty_content(client, post_accounts, payload):
    response = client.post(
        "/api/post",
        json=payload,
        headers=bearer(post_accounts["owner_token"]),
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "內容不能為空"}


def test_post_content_length_is_enforced_on_create_and_update(
    client, app, post_accounts
):
    headers = bearer(post_accounts["owner_token"])
    accepted_content = "文" * POST_CONTENT_MAX_LENGTH
    created = client.post(
        "/api/post", json={"content": accepted_content}, headers=headers
    )
    assert created.status_code == 200

    with app.app_context():
        post = Post.query.filter_by(user_id=post_accounts["owner_id"]).one()
        post_id = post.id
        assert post.content == accepted_content

    too_long = "文" * (POST_CONTENT_MAX_LENGTH + 1)
    rejected_create = client.post(
        "/api/post", json={"content": too_long}, headers=headers
    )
    rejected_update = client.put(
        f"/api/post/{post_id}", json={"content": too_long}, headers=headers
    )

    expected = {"error": f"內容不可超過 {POST_CONTENT_MAX_LENGTH} 個字元"}
    assert rejected_create.status_code == 400
    assert rejected_create.get_json() == expected
    assert rejected_update.status_code == 400
    assert rejected_update.get_json() == expected

    with app.app_context():
        assert db.session.get(Post, post_id).content == accepted_content


def test_post_crud_and_owner_permissions(client, app, post_accounts):
    owner_headers = bearer(post_accounts["owner_token"])
    reader_headers = bearer(post_accounts["reader_token"])

    create_response = client.post(
        "/api/post",
        json={"content": "  A post covered by pytest  "},
        headers=owner_headers,
    )
    assert create_response.status_code == 200
    assert create_response.get_json() == {"message": "貼文已新增"}

    with app.app_context():
        post = Post.query.filter_by(user_id=post_accounts["owner_id"]).one()
        post_id = post.id
        assert post.content == "A post covered by pytest"

    forbidden_update = client.put(
        f"/api/post/{post_id}",
        json={"content": "Reader edit"},
        headers=reader_headers,
    )
    assert forbidden_update.status_code == 403

    empty_update = client.put(
        f"/api/post/{post_id}", json=None, headers=owner_headers
    )
    assert empty_update.status_code == 400
    assert empty_update.get_json() == {"error": "內容不能為空"}

    update_response = client.put(
        f"/api/post/{post_id}",
        json={"content": "  Updated post  "},
        headers=owner_headers,
    )
    assert update_response.status_code == 200
    assert update_response.get_json() == {"message": "已更新"}

    with app.app_context():
        assert db.session.get(Post, post_id).content == "Updated post"

    forbidden_delete = client.delete(f"/api/post/{post_id}", headers=reader_headers)
    assert forbidden_delete.status_code == 403

    delete_response = client.delete(f"/api/post/{post_id}", headers=owner_headers)
    assert delete_response.status_code == 200
    assert delete_response.get_json() == {"message": "已刪除"}

    with app.app_context():
        assert db.session.get(Post, post_id) is None


@pytest.mark.parametrize("method", ["post", "put", "delete"])
def test_post_item_endpoints_return_not_found(client, post_accounts, method):
    path = "/api/post/999999999"
    if method == "post":
        path += "/like"
    kwargs = {"json": {"content": "missing"}} if method == "put" else {}

    response = getattr(client, method)(
        path, headers=bearer(post_accounts["owner_token"]), **kwargs
    )

    assert response.status_code == 404


def test_like_toggle_updates_count_and_list_flags(client, app, post_accounts):
    with app.app_context():
        post = Post(content="Like me", user_id=post_accounts["owner_id"])
        db.session.add(post)
        db.session.commit()
        post_id = post.id

    owner_headers = bearer(post_accounts["owner_token"])
    reader_headers = bearer(post_accounts["reader_token"])

    owner_like = client.post(f"/api/post/{post_id}/like", headers=owner_headers)
    assert owner_like.status_code == 200
    assert owner_like.get_json() == {"liked_by_me": True, "like_count": 1}

    reader_like = client.post(f"/api/post/{post_id}/like", headers=reader_headers)
    assert reader_like.status_code == 200
    assert reader_like.get_json() == {"liked_by_me": True, "like_count": 2}

    all_posts = client.get("/api/post", headers=owner_headers).get_json()
    listed = next(item for item in all_posts if item["id"] == post_id)
    assert listed == {
        "id": post_id,
        "content": "Like me",
        "created_at": listed["created_at"],
        "user_id": post_accounts["owner_id"],
        "like_count": 2,
        "liked_by_me": True,
        "user": {
            "id": post_accounts["owner_id"],
            "username": listed["user"]["username"],
            "nickname": "Post Owner",
            "avatar_url": "https://example.com/owner.png",
            "role": "user",
        },
    }
    assert listed["user"]["username"].startswith("post-owner-")
    assert listed["created_at"]

    unlike = client.post(f"/api/post/{post_id}/like", headers=owner_headers)
    assert unlike.status_code == 200
    assert unlike.get_json() == {"liked_by_me": False, "like_count": 1}

    my_post = next(
        item
        for item in client.get("/api/post/me", headers=owner_headers).get_json()
        if item["id"] == post_id
    )
    assert "user" not in my_post
    assert my_post["like_count"] == 1
    assert my_post["liked_by_me"] is False


def test_post_lists_are_paginated_and_my_posts_are_user_scoped(
    client, app, post_accounts
):
    start = datetime(2099, 1, 1)
    with app.app_context():
        posts = []
        for index in range(4):
            posts.append(
                Post(
                    content=f"owner-page-{index}",
                    user_id=post_accounts["owner_id"],
                    created_at=start + timedelta(minutes=index),
                )
            )
        posts.append(
            Post(
                content="reader-only",
                user_id=post_accounts["reader_id"],
                created_at=start + timedelta(minutes=10),
            )
        )
        db.session.add_all(posts)
        db.session.commit()

    owner_headers = bearer(post_accounts["owner_token"])
    page_one = client.get(
        "/api/post/me?page=1&per_page=2", headers=owner_headers
    ).get_json()
    page_two = client.get(
        "/api/post/me?page=2&per_page=2", headers=owner_headers
    ).get_json()
    normalized = client.get(
        "/api/post/me?page=0&per_page=-3", headers=owner_headers
    ).get_json()
    capped = client.get(
        "/api/post/me?page=1&per_page=500", headers=owner_headers
    ).get_json()

    assert [item["content"] for item in page_one] == ["owner-page-3", "owner-page-2"]
    assert [item["content"] for item in page_two] == ["owner-page-1", "owner-page-0"]
    assert [item["content"] for item in normalized] == ["owner-page-3"]
    assert len(capped) == 4
    assert all(item["user_id"] == post_accounts["owner_id"] for item in capped)

    global_page = client.get(
        "/api/post?page=1&per_page=2", headers=owner_headers
    ).get_json()
    assert [item["content"] for item in global_page] == ["reader-only", "owner-page-3"]
