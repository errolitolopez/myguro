"""Maintenance mode: while the admin has it on, everyone but the admin gets the maintenance page (503)."""

from flask import jsonify, render_template, request

from myguro.database import get_db
from myguro.domain import maintenance
from myguro.domain.maintenance import DEFAULT_MESSAGE
from myguro.errors import say
from myguro.services import SettingsService
from myguro.web.security import current_user

# Open even during maintenance: the files every page needs, and signing in and out. Without the sign-in the
# admin could not get in to turn it off. Anyone else may sign in too: the next page they open is the maintenance page.
OPEN_ENDPOINTS = {"static", "favicon", "auth.index", "auth.login_page", "auth.api_login", "auth.api_logout"}
RETRY_AFTER_SECONDS = 300  # a hint for browsers and search engines; the page does not reload by itself


def refuse_during_maintenance():
    """before_request: None to carry on, or the 503 answer for someone kept out. One small query per request."""
    if request.endpoint in OPEN_ENDPOINTS:
        return None
    state = SettingsService(get_db()).maintenance()
    user = current_user()
    if not state["enabled"] or (user is not None and not maintenance.blocks(user["role"])):
        return None
    message = state["message"] or say(DEFAULT_MESSAGE)  # the admin's own note is shown as written
    if request.path.startswith("/api/"):
        response = jsonify(error=message, maintenance=True)
    else:
        response = render_template("maintenance.html", message=message, user=user)
    return response, 503, {"Retry-After": str(RETRY_AFTER_SECONDS)}


def register(app):
    app.before_request(refuse_during_maintenance)
