"""The Settings page (every role: appearance and account), the admin's System settings page (school-wide) and the API."""

from flask import Blueprint, jsonify, render_template

from myguro.database import get_db
from myguro.services import SettingsService
from myguro.web.security import current_user, json_body, role_required_api, role_required_page

bp = Blueprint("settings", __name__)


def service():
    return SettingsService(get_db(), current_user())


@bp.get("/settings")
@role_required_page("admin", "teacher", "student", "supervisor")
def page():
    return render_template("settings.html", user=current_user())


@bp.get("/system-settings")
@role_required_page("admin")
def system_page():
    return render_template("system_settings.html", user=current_user())


@bp.get("/api/settings")
@role_required_api("admin", "teacher", "student")
def api_get():
    return jsonify(settings=service().get())


@bp.put("/api/settings")
@role_required_api("admin")
def api_update():
    return jsonify(settings=service().update(json_body()))
