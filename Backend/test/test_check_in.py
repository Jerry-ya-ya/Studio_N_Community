from datetime import date, datetime
from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token

from models import DailyCheckIn, User, db
from routes.check_in import check_in as check_in_module


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def check_in_account(app):
    suffix = uuid4().hex
    with app.app_context():
        user = User(
            username=f"check-in-user-{suffix}",
            email=f"check-in-user-{suffix}@example.com",
            password="test-password",
            email_verified=True,
        )
        db.session.add(user)
        db.session.commit()
        account = {
            "id": user.id,
            "token": create_access_token(identity=str(user.id)),
        }

    yield account

    with app.app_context():
        DailyCheckIn.query.filter_by(user_id=account["id"]).delete()
        User.query.filter_by(id=account["id"]).delete()
        db.session.commit()


def freeze_taipei_now(monkeypatch, value):
    monkeypatch.setattr(check_in_module, "taipei_now", lambda: value)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/check-in/status"),
        ("get", "/api/check-in/history"),
        ("post", "/api/check-in"),
    ],
)
def test_check_in_endpoints_require_authentication(client, method, path):
    response = getattr(client, method)(path)

    assert response.status_code == 401


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/check-in/status"),
        ("get", "/api/check-in/history"),
        ("post", "/api/check-in"),
    ],
)
def test_check_in_endpoints_reject_tokens_for_missing_users(
    app, client, method, path
):
    with app.app_context():
        token = create_access_token(identity="999999999")

    response = getattr(client, method)(path, headers=bearer(token))

    assert response.status_code == 404
    assert response.get_json() == {"error": "User not found"}


def test_status_returns_points_and_last_seven_days(
    app, client, check_in_account, monkeypatch
):
    now = datetime(2026, 9, 10, 18, 30)
    freeze_taipei_now(monkeypatch, now)
    with app.app_context():
        db.session.add_all([
            DailyCheckIn(
                user_id=check_in_account["id"],
                checkin_date=date(2026, 9, 4),
                points=1,
            ),
            DailyCheckIn(
                user_id=check_in_account["id"],
                checkin_date=date(2026, 9, 5),
                points=5,
            ),
            DailyCheckIn(
                user_id=check_in_account["id"],
                checkin_date=date(2026, 9, 7),
                points=1,
            ),
            DailyCheckIn(
                user_id=check_in_account["id"],
                checkin_date=date(2026, 9, 10),
                points=1,
                created_at=now,
            ),
        ])
        db.session.commit()

    response = client.get(
        "/api/check-in/status",
        headers=bearer(check_in_account["token"]),
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {
        "checkedInToday": True,
        "today": "2026-09-10",
        "todayPoints": 1,
        "isWeekend": False,
        "totalPoints": 8,
        "lastCheckIn": "2026-09-10T18:30:00+08:00",
        "lastSevenDays": {
            "checkedDays": 4,
            "totalDays": 7,
            "days": [
                {"date": "2026-09-04", "checked": True, "points": 1},
                {"date": "2026-09-05", "checked": True, "points": 5},
                {"date": "2026-09-06", "checked": False, "points": 5},
                {"date": "2026-09-07", "checked": True, "points": 1},
                {"date": "2026-09-08", "checked": False, "points": 1},
                {"date": "2026-09-09", "checked": False, "points": 1},
                {"date": "2026-09-10", "checked": True, "points": 1},
            ],
        },
    }


def test_status_returns_empty_state_for_user_without_check_ins(
    client, check_in_account, monkeypatch
):
    freeze_taipei_now(monkeypatch, datetime(2026, 9, 12, 9, 0))

    response = client.get(
        "/api/check-in/status",
        headers=bearer(check_in_account["token"]),
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["checkedInToday"] is False
    assert payload["lastCheckIn"] is None
    assert payload["totalPoints"] == 0
    assert payload["todayPoints"] == 5
    assert payload["isWeekend"] is True
    assert payload["lastSevenDays"]["checkedDays"] == 0


@pytest.mark.parametrize(
    ("query", "error"),
    [
        ("year=not-a-number", "Year must be a number"),
        ("year=1999", "Year must be between 2000 and 2026"),
        ("year=2027", "Year must be between 2000 and 2026"),
    ],
)
def test_history_validates_year(client, check_in_account, monkeypatch, query, error):
    freeze_taipei_now(monkeypatch, datetime(2026, 9, 10, 12, 0))

    response = client.get(
        f"/api/check-in/history?{query}",
        headers=bearer(check_in_account["token"]),
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": error}


def test_history_filters_sorts_and_reports_available_years(
    app, client, check_in_account, monkeypatch
):
    freeze_taipei_now(monkeypatch, datetime(2026, 9, 10, 12, 0))
    with app.app_context():
        db.session.add_all([
            DailyCheckIn(
                user_id=check_in_account["id"],
                checkin_date=date(2025, 12, 31),
                points=1,
            ),
            DailyCheckIn(
                user_id=check_in_account["id"],
                checkin_date=date(2024, 6, 15),
                points=5,
            ),
            DailyCheckIn(
                user_id=check_in_account["id"],
                checkin_date=date(2025, 1, 2),
                points=1,
            ),
            DailyCheckIn(
                user_id=check_in_account["id"],
                checkin_date=date(2026, 1, 1),
                points=1,
            ),
        ])
        db.session.commit()

    selected_year = client.get(
        "/api/check-in/history?year=2025",
        headers=bearer(check_in_account["token"]),
    )
    current_year = client.get(
        "/api/check-in/history",
        headers=bearer(check_in_account["token"]),
    )

    assert selected_year.status_code == 200
    assert selected_year.get_json() == {
        "year": 2025,
        "checkedDates": ["2025-01-02", "2025-12-31"],
        "availableYears": [2026, 2025, 2024],
    }
    assert current_year.status_code == 200
    assert current_year.get_json()["checkedDates"] == ["2026-01-01"]


def test_history_without_check_ins_only_offers_current_year(
    client, check_in_account, monkeypatch
):
    freeze_taipei_now(monkeypatch, datetime(2026, 9, 10, 12, 0))

    response = client.get(
        "/api/check-in/history",
        headers=bearer(check_in_account["token"]),
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "year": 2026,
        "checkedDates": [],
        "availableYears": [2026],
    }


@pytest.mark.parametrize(
    ("now", "expected_points"),
    [
        (datetime(2026, 9, 11, 8, 0), 1),
        (datetime(2026, 9, 12, 8, 0), 5),
    ],
)
def test_create_check_in_awards_daily_points_once(
    app, client, check_in_account, monkeypatch, now, expected_points
):
    freeze_taipei_now(monkeypatch, now)
    headers = bearer(check_in_account["token"])

    created = client.post("/api/check-in", headers=headers)
    duplicate = client.post("/api/check-in", headers=headers)

    assert created.status_code == 201
    assert created.get_json()["earnedPoints"] == expected_points
    assert created.get_json()["message"] == "checked in"
    assert created.get_json()["totalPoints"] == expected_points
    assert created.get_json()["checkedInToday"] is True
    assert duplicate.status_code == 200
    assert duplicate.get_json()["message"] == "already checked in today"
    assert "earnedPoints" not in duplicate.get_json()
    assert duplicate.get_json()["totalPoints"] == expected_points

    with app.app_context():
        check_ins = DailyCheckIn.query.filter_by(
            user_id=check_in_account["id"],
            checkin_date=now.date(),
        ).all()
        assert len(check_ins) == 1
        assert check_ins[0].points == expected_points
