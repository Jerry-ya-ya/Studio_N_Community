def test_register_success(client):
    payload = {
        "username": "testregisteruser",
        "email": "testregisteruser@example.com",
        "password": "Orbit!Cedar47Path"
    }

    resp = client.post("/api/register", json=payload)

    assert resp.status_code == 201
