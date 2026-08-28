from flask_jwt_extended import create_access_token
from werkzeug.security import check_password_hash, generate_password_hash

from models import User, db
from password_policy import validate_password


STRONG_PASSWORD = "Orbit!Cedar47Path"


def test_password_policy_accepts_a_strong_password():
    assert validate_password(STRONG_PASSWORD) == []


def test_password_policy_rejects_short_common_and_identity_passwords():
    assert validate_password("123456")
    assert validate_password("password123")
    assert validate_password(
        "AccountOwner!47",
        username="accountowner",
        email="owner@example.com",
    ) == ["密碼不得包含帳號或 Email 名稱"]


def test_register_rejects_weak_password_before_creating_user(client, app):
    payload = {
        "username": "weak-password-register",
        "email": "weak-password-register@example.com",
        "password": "123456",
    }

    response = client.post(
        "/api/register",
        json=payload,
        environ_overrides={"REMOTE_ADDR": "203.0.113.30"},
    )

    assert response.status_code == 400
    assert response.get_json()["code"] == "weak_password"
    with app.app_context():
        assert User.query.filter_by(username=payload["username"]).first() is None


def test_change_password_rejects_weak_new_password(client, app):
    original_password = "Original!Cedar47Path"
    with app.app_context():
        user = User(
            username="password-policy-change-user",
            email="password-policy-change@example.com",
            password=generate_password_hash(original_password),
            email_verified=True,
            role="user",
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        token = create_access_token(identity=str(user_id))

    response = client.put(
        "/api/changepassword",
        json={"old_password": original_password, "new_password": "123456"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.get_json()["code"] == "weak_password"

    with app.app_context():
        user = db.session.get(User, user_id)
        assert check_password_hash(user.password, original_password)
