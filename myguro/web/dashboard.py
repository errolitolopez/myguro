from flask import Blueprint, jsonify, redirect, render_template, url_for

from myguro.database import get_db
from myguro.services import BackupService, DashboardService, RecoveryService
from myguro.web.security import current_user, login_required_page, role_required_api

bp = Blueprint("dashboard", __name__)


@bp.get("/dashboard")
@login_required_page
def page():
    if current_user()["role"] == "supervisor":  # a supervisor's only page is the activity log
        return redirect(url_for("log.page"))
    user = current_user()
    backup = BackupService(get_db(), user).status() if user["role"] == "admin" else None
    no_recovery_code = not RecoveryService(get_db(), user).status()["has_code"]
    return render_template("dashboard.html", user=user, backup=backup, no_recovery_code=no_recovery_code)


@bp.get("/api/dashboard")
@role_required_api("admin", "teacher", "student")
def api_dashboard():
    return jsonify(DashboardService(get_db(), current_user()).data())
