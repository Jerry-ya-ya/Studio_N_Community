import os
from dotenv import load_dotenv
load_dotenv()

def test_register_success(client):
    payload = {
        "email": os.getenv("SUPERADMIN_EMAIL"),
        "username": os.getenv("SUPERADMIN_USERNAME"),
        "password": "Orbit!Cedar47Path",
    }

    resp = client.post("/api/register", json=payload)

    assert resp.status_code == 201
