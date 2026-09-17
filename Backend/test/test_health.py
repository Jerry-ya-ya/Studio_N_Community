from flask import Flask

from app import configure_trusted_proxy
from routes.test.health import health_bp


def test_health_ok(client):
    resp = client.get("/api/healthz")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok", "scheme": "http"}


def test_health_reports_original_https_scheme_behind_production_proxy():
    app = Flask(__name__)
    app.config["TRUSTED_PROXY_HOPS"] = 1
    configure_trusted_proxy(app)
    app.register_blueprint(health_bp, url_prefix="/api")

    resp = app.test_client().get(
        "/api/healthz",
        headers={"X-Forwarded-Proto": "https"},
    )

    assert resp.status_code == 200
    assert resp.get_json()["scheme"] == "https"
