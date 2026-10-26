"""Recovery codes: make one (logged in), and choose a new password with one (forgot the password)."""

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for

from myguro.database import get_db
from myguro.services import RecoveryService
from myguro.web.security import current_user, json_body, login_required_api, login_required_page

bp = Blueprint("recovery", __name__)


@bp.get("/forgot-password")
def forgot_page():
    if current_user():
        return redirect(url_for("dashboard.page"))
    return render_template("forgot_password.html")


@bp.get("/recovery-code")
@login_required_page
def code_page():
    return render_template("recovery_code.html", user=current_user())


@bp.get("/api/recovery-code")
@login_required_api
def api_status():
    return jsonify(RecoveryService(get_db(), current_user()).status())


@bp.post("/api/recovery-code")
@login_required_api
def api_create():
    """{current_password, replace} -> {code}: shown once. If there is a code already, replace must be true."""
    data = json_body()
    return jsonify(RecoveryService(get_db(), current_user()).create(data.get("current_password"),
                                                                    data.get("replace"))), 201


@bp.post("/api/recover")
def api_recover():
    """{username, code, new_password} -> {code}: the new recovery code. No login needed (the person forgot the password)."""
    data = json_body()
    return jsonify(RecoveryService(get_db()).recover(
        data.get("username"), data.get("code"), data.get("new_password"), request.remote_addr,
        current_app.extensions["login_throttle"]))
