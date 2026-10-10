from flask import Blueprint, jsonify, render_template

from myguro.database import get_db
from myguro.services import DashboardService
from myguro.web.security import current_user, login_required_api, login_required_page

bp = Blueprint("dashboard", __name__)


@bp.get("/dashboard")
@login_required_page
def page():
    return render_template("dashboard.html", user=current_user())


@bp.get("/api/dashboard")
@login_required_api
def api_dashboard():
    return jsonify(DashboardService(get_db(), current_user()).data())
