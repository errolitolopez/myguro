"""Admin: the Settings page and its API."""

from flask import Blueprint, jsonify, render_template

from myguro.database import get_db
from myguro.services import SettingsService
from myguro.web.security import current_user, json_body, login_required_api, role_required_api, role_required_page

bp = Blueprint("settings", __name__)


def service():
    return SettingsService(get_db(), current_user())


@bp.get("/settings")
@role_required_page("admin")
def page():
    return render_template("settings.html", user=current_user())


@bp.get("/api/settings")
@login_required_api
def api_get():
    return jsonify(settings=service().get())


@bp.put("/api/settings")
@role_required_api("admin")
def api_update():
    return jsonify(settings=service().update(json_body()))
