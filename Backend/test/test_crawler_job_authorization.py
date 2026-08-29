from uuid import uuid4
from unittest.mock import patch

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from models import User, db


def token_for_role(app, role):
    suffix = uuid4().hex
    with app.app_context():
        user = User(
            username=f"crawler-{role}-{suffix}",
            email=f"crawler-{role}-{suffix}@example.com",
            password=generate_password_hash("StrongPass123!"),
            email_verified=True,
            role=role,
        )
        db.session.add(user)
        db.session.commit()
        return create_access_token(identity=str(user.id), additional_claims={"role": role})


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_crawler_jobs_reject_unauthenticated_requests(client):
    assert client.post("/api/crawler/fetch").status_code == 401
    assert client.post("/api/crawler/test").status_code == 401


def test_crawler_jobs_reject_regular_users(app, client):
    headers = auth_header(token_for_role(app, "user"))

    assert client.post("/api/crawler/fetch", headers=headers).status_code == 403
    assert client.post("/api/crawler/test", headers=headers).status_code == 403


def test_admin_can_trigger_crawler_jobs(app, client):
    headers = auth_header(token_for_role(app, "admin"))

    with patch("routes.crawler.crawler.fetch_and_store_news", return_value=2) as fetch:
        response = client.post("/api/crawler/fetch", headers=headers)
        assert response.status_code == 200
        fetch.assert_called_once_with()

    with patch("routes.crawler.crawler.hello.delay") as delay:
        response = client.post("/api/crawler/test", headers=headers)
        assert response.status_code == 200
        delay.assert_called_once_with()


def test_crawler_test_get_cannot_enqueue_work(app, client):
    headers = auth_header(token_for_role(app, "admin"))

    with patch("routes.crawler.crawler.hello.delay") as delay:
        response = client.get("/api/crawler/test", headers=headers)
        assert response.status_code == 405
        delay.assert_not_called()
