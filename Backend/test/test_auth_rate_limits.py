def post_from(client, path, payload, remote_addr):
    return client.post(
        path,
        json=payload,
        environ_overrides={"REMOTE_ADDR": remote_addr},
    )


def assert_rate_limited(response):
    assert response.status_code == 429
    assert response.get_json() == {
        "error": "請求過於頻繁，請稍後再試",
        "code": "rate_limit_exceeded",
    }


def test_login_limits_repeated_failures_for_the_same_username(client):
    remote_addr = "203.0.113.10"
    payload = {"username": "rate-limit-login", "password": "wrong"}

    for _ in range(5):
        response = post_from(client, "/api/login", payload, remote_addr)
        assert response.status_code == 401

    assert_rate_limited(post_from(client, "/api/login", payload, remote_addr))


def test_register_limits_repeated_requests_for_the_same_email(client):
    remote_addr = "203.0.113.11"
    payload = {"email": "rate-limit-register@example.com"}

    for _ in range(3):
        response = post_from(client, "/api/register", payload, remote_addr)
        assert response.status_code == 400

    assert_rate_limited(post_from(client, "/api/register", payload, remote_addr))


def test_resend_verification_limits_repeated_requests_for_the_same_email(client):
    remote_addr = "203.0.113.12"
    payload = {"email": "rate-limit-resend@example.com"}

    for _ in range(3):
        response = post_from(client, "/api/resendverification", payload, remote_addr)
        assert response.status_code == 404

    assert_rate_limited(
        post_from(client, "/api/resendverification", payload, remote_addr)
    )
