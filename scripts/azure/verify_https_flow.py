#!/usr/bin/env python3
"""Verify the deployed HTTPS proxy and authentication flow.

This test intentionally uses only the public frontend origin. A successful run
therefore proves that the internal Backend Container App can be reached without
publishing its ingress.
"""

from __future__ import annotations

import argparse
from http.cookiejar import CookieJar
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, HTTPCookieProcessor, Request, build_opener
from urllib.parse import urljoin, urlparse


def require_https_url(value: str, label: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{label} must be an absolute HTTPS URL")
    return value.rstrip("/")


def cookie(jar: CookieJar, name: str):
    matches = [item for item in jar if item.name == name]
    if not matches:
        raise AssertionError(f"missing {name} cookie")
    return matches[-1]


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_json(opener, url: str, timeout: float, payload=None, headers=None):
    request_headers = {"Accept": "application/json", **(headers or {})}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=request_headers, method="POST" if data is not None else "GET")
    try:
        response = opener.open(request, timeout=timeout)
    except HTTPError as exc:
        response = exc
    body = response.read()
    parsed = json.loads(body) if body else None
    return response.status, response.headers, parsed


def run(base_url: str, username: str, password: str, verification_url: str, timeout: float) -> dict:
    base_url = require_https_url(base_url, "base URL")
    verification_url = require_https_url(verification_url, "verification URL")
    if urlparse(verification_url).netloc != urlparse(base_url).netloc:
        raise AssertionError("verification URL must use the public frontend origin")

    jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar), NoRedirect())

    health_status, _, health_payload = request_json(
        opener, urljoin(f"{base_url}/", "api/healthz"), timeout
    )
    if health_status != 200:
        raise AssertionError(f"health endpoint returned {health_status}")
    if health_payload != {"status": "ok", "scheme": "https"}:
        raise AssertionError(f"backend observed the wrong scheme: {health_payload!r}")

    login_status, _, login_payload = request_json(
        opener,
        urljoin(f"{base_url}/", "api/login"),
        timeout,
        payload={"username": username, "password": password, "remember_me": True},
    )
    if login_status != 200:
        raise AssertionError(f"login returned {login_status}: {login_payload!r}")
    if not login_payload.get("access_token"):
        raise AssertionError("login response did not contain an access token")

    refresh_before = cookie(jar, "refresh_token_cookie")
    csrf_before = cookie(jar, "csrf_refresh_token")
    if not refresh_before.secure or refresh_before.path != "/api/refresh":
        raise AssertionError("refresh cookie is missing Secure or the restricted path")
    if not refresh_before.has_nonstandard_attr("HttpOnly"):
        raise AssertionError("refresh cookie is missing HttpOnly")
    if not csrf_before.secure:
        raise AssertionError("refresh CSRF cookie is missing Secure")

    refresh_value_before = refresh_before.value
    refresh_status, _, refresh_payload = request_json(
        opener,
        urljoin(f"{base_url}/", "api/refresh"),
        timeout,
        payload={},
        headers={"X-CSRF-TOKEN": csrf_before.value},
    )
    if refresh_status != 200:
        raise AssertionError(f"refresh returned {refresh_status}: {refresh_payload!r}")
    if not refresh_payload.get("access_token"):
        raise AssertionError("refresh response did not contain an access token")
    if cookie(jar, "refresh_token_cookie").value == refresh_value_before:
        raise AssertionError("refresh token cookie was not rotated")

    verification_request = Request(verification_url, method="GET")
    try:
        verification = opener.open(verification_request, timeout=timeout)
    except HTTPError as exc:
        verification = exc
    if verification.status not in (301, 302, 303, 307, 308):
        raise AssertionError(f"verification link returned {verification.status}, expected a redirect")
    expected_location = f"{base_url}/register/verified"
    if verification.headers.get("Location") != expected_location:
        raise AssertionError(
            f"verification link redirected to {verification.headers.get('Location')!r}, "
            f"expected {expected_location!r}"
        )

    return {
        "https_forwarding": "passed",
        "login": "passed",
        "secure_refresh_cookie": "passed",
        "refresh_rotation": "passed",
        "verification_link": "passed",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("SMOKE_BASE_URL"))
    parser.add_argument("--username", default=os.getenv("SMOKE_USERNAME"))
    parser.add_argument("--password", default=os.getenv("SMOKE_PASSWORD"))
    parser.add_argument("--verification-url", default=os.getenv("SMOKE_VERIFICATION_URL"))
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()

    missing = [
        name
        for name, value in (
            ("base-url", args.base_url),
            ("username", args.username),
            ("password", args.password),
            ("verification-url", args.verification_url),
        )
        if not value
    ]
    if missing:
        parser.error(f"missing required values: {', '.join(missing)}")

    try:
        result = run(args.base_url, args.username, args.password, args.verification_url, args.timeout)
    except (AssertionError, OSError, URLError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1

    print(json.dumps({"status": "passed", "checks": result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
