"""The device name in the sign-in log: a short "Chrome on Windows", never the raw User-Agent text."""

import sqlite3

from conftest import PASSWORD, flask_app
from myguro.migrations import add_missing_columns
from myguro.domain.device import MAX_DEVICE_LENGTH, device_name

CHROME_WINDOWS = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/130.0.0.0 Safari/537.36")
EDGE_WINDOWS = CHROME_WINDOWS + " Edg/130.0.0.0"
SAFARI_IPHONE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
                 "Version/17.5 Mobile/15E148 Safari/604.1")
CHROME_ANDROID = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/130.0.0.0 Mobile Safari/537.36")
FIREFOX_LINUX = "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0"
SAFARI_MAC = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) "
              "Version/17.5 Safari/605.1.15")


def test_known_browsers_and_systems_are_named():
    assert device_name(CHROME_WINDOWS) == "Chrome on Windows"
    assert device_name(EDGE_WINDOWS) == "Edge on Windows"  # Edge also says Chrome and Safari
    assert device_name(SAFARI_IPHONE) == "Safari on iPhone"  # an iPhone also says Mac OS X
    assert device_name(CHROME_ANDROID) == "Chrome on Android"  # Android also says Linux
    assert device_name(FIREFOX_LINUX) == "Firefox on Linux"
    assert device_name(SAFARI_MAC) == "Safari on Mac"


def test_unknown_or_missing_text_gives_a_short_answer_never_the_raw_text():
    assert device_name("") == "" and device_name(None) == ""
    assert device_name("curl/8.5.0") == ""
    assert device_name("SomeBot/1.0 (Android)") == "Android"
    assert len(device_name("Chrome/1 " + "Windows " * 100)) <= MAX_DEVICE_LENGTH


def sign_in_entries(admin):
    return [entry for entry in admin.get("/api/log?per_page=100&category=sign-in").get_json()["entries"]]


def test_a_sign_in_keeps_the_device_name_and_not_the_user_agent(admin):
    client = flask_app.test_client()
    assert client.post("/api/login", json={"username": "jdelacruz01", "password": PASSWORD},
                       headers={"User-Agent": SAFARI_IPHONE}).status_code == 200
    entry = next(e for e in sign_in_entries(admin) if e["action"] == "auth.login"
                 and e["actor"]["username"] == "jdelacruz01")
    assert entry["device"] == "Safari on iPhone"
    assert "Mozilla" not in str(entry)


def test_a_wrong_password_also_keeps_the_device(admin):
    flask_app.test_client().post("/api/login", json={"username": "jdelacruz01", "password": "nope"},
                                 headers={"User-Agent": CHROME_ANDROID})
    entry = next(e for e in sign_in_entries(admin) if e["action"] == "auth.login_failed")
    assert entry["device"] == "Chrome on Android"


def test_other_entries_have_no_device(admin):
    entries = admin.get("/api/log?per_page=100").get_json()["entries"]
    assert all(entry["device"] == "" for entry in entries if entry["category"] != "sign-in")


def test_an_old_database_gets_the_device_column():
    """A log table made before the column existed is given it (existing entries get an empty device)."""
    connection = sqlite3.connect(flask_app.config["DATABASE"])
    connection.row_factory = sqlite3.Row
    connection.execute("ALTER TABLE activity_log RENAME TO activity_log_new")
    connection.execute("CREATE TABLE activity_log (id INTEGER PRIMARY KEY, at TEXT NOT NULL DEFAULT (datetime('now')), "
                       "summary TEXT NOT NULL, address TEXT NOT NULL DEFAULT '')")
    connection.execute("INSERT INTO activity_log (summary, address) VALUES ('Logged in.', '1.2.3.4')")
    add_missing_columns(connection)
    row = connection.execute("SELECT * FROM activity_log").fetchone()
    assert row["address"] == "1.2.3.4" and row["device"] == ""
    connection.execute("DROP TABLE activity_log")
    connection.execute("DROP TABLE activity_log_new")  # its indexes go with it; init-db below makes the real ones again
    connection.commit()
    connection.close()
    assert flask_app.test_cli_runner().invoke(args=["init-db"]).exit_code == 0
