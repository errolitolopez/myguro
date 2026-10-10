"""App settings that aren't business rules: where things are stored, time zone, sessions."""

import os
import secrets
from datetime import datetime
from zoneinfo import ZoneInfo

# Due dates are calendar days at the school, wherever the server runs.
SCHOOL_TIMEZONE = ZoneInfo("Asia/Manila")


def school_today():
    return datetime.now(SCHOOL_TIMEZONE).date()


def school_now_text():
    """"2026-10-10 16:35" in the school's time zone."""
    return datetime.now(SCHOOL_TIMEZONE).strftime("%Y-%m-%d %H:%M")


def configure(app, test_config=None):
    """Set the database path, secret key and cookie settings on the Flask app."""
    # The instance/ folder holds private files (database, secret key). It is not committed to git.
    os.makedirs(app.instance_path, exist_ok=True)
    app.config["DATABASE"] = os.environ.get("MYGURO_DATABASE", os.path.join(app.instance_path, "myguro.db"))
    # No "remember me": the login ends when the browser is closed, since school computers are shared.
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.secret_key = load_secret_key(app.instance_path)
    if test_config:
        app.config.update(test_config)


def load_secret_key(instance_path):
    """The secret key signs the login cookie. Create one the first time and reuse it after."""
    path = os.path.join(instance_path, "secret_key")
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(secrets.token_hex(32))
    with open(path) as f:
        return f.read().strip()
