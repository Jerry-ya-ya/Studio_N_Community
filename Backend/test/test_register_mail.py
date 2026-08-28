import re

def test_register_email_contains_verify_url(client, mocker):
    mock_send = mocker.patch("routes.auth.email.mail.send")

    payload = {
        "email": "testregisteremail@example.com",
        "password": "Orbit!Cedar47Path",
        "username": "testregisteremail"
    }

    resp = client.post("/api/register", json=payload)

    assert resp.status_code == 201
    mock_send.assert_called_once()

    msg = mock_send.call_args[0][0]
    assert msg.recipients == ["testregisteremail@example.com"]

    body = msg.body
    match = re.search(r"http://[^\s]+|https://[^\s]+|/api/[^\s]+", body)
    assert match is not None

    verify_url = match.group(0)

    if verify_url.startswith("/"):
        verify_resp = client.get(verify_url)
    else:
        # 如果 body 裡是完整 URL，要切出 path
        from urllib.parse import urlparse
        path = urlparse(verify_url).path
        query = urlparse(verify_url).query
        full_path = f"{path}?{query}" if query else path
        verify_resp = client.get(full_path)

    assert verify_resp.status_code == 200
