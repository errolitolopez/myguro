"""The address shown in the activity log: the person's device, also when the site is behind a proxy."""

import pytest

from conftest import PASSWORD, flask_app


def sign_in_address(admin, headers=None, username="jdelacruz01"):
    """Log in from a fresh client with these headers, then read the address the log kept for it."""
    response = flask_app.test_client().post("/api/login", json={"username": username, "password": PASSWORD},
                                            headers=headers or {})
    assert response.status_code == 200
    entries = admin.get("/api/log?per_page=100").get_json()["entries"]
    return next(entry["address"] for entry in entries if entry["action"] == "auth.login"
                and entry["actor"]["username"] == username)


@pytest.fixture
def behind_proxy():
    flask_app.config["TRUST_PROXY"] = True
    yield
    flask_app.config["TRUST_PROXY"] = False


def test_without_a_proxy_the_headers_are_ignored(admin):
    # Anyone could send these, so they are not believed unless the server says a proxy sets them
    assert sign_in_address(admin, {"X-Real-IP": "203.0.113.7", "X-Forwarded-For": "198.51.100.1"}) == "127.0.0.1"


def test_behind_a_proxy_the_real_address_is_used(admin, behind_proxy):
    assert sign_in_address(admin, {"X-Real-IP": "203.0.113.7"}) == "203.0.113.7"


def test_forwarded_for_uses_the_last_entry(admin, behind_proxy):
    # The first entries can be made up by the visitor; the last one was added by our own proxy
    assert sign_in_address(admin, {"X-Forwarded-For": "6.6.6.6, 203.0.113.9"}) == "203.0.113.9"


def test_a_made_up_or_missing_header_falls_back_to_the_direct_address(admin, behind_proxy):
    assert sign_in_address(admin, {"X-Real-IP": "not an address"}) == "127.0.0.1"
    assert sign_in_address(admin, {}) == "127.0.0.1"
    assert sign_in_address(admin, {"X-Real-IP": "2001:db8::1"}) == "2001:db8::1"  # IPv6 works too


def test_the_lock_out_is_per_address_behind_a_proxy(admin, behind_proxy):
    def wrong(address):
        return flask_app.test_client().post("/api/login", json={"username": "jdelacruz01", "password": "nope"},
                                            headers={"X-Real-IP": address}).status_code
    assert [wrong("203.0.113.7") for _ in range(6)] == [401, 401, 401, 401, 401, 429]
    assert wrong("203.0.113.8") == 401  # another device is not locked out by it
