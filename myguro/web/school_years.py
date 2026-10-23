"""School years: pick the year to look at (everyone), start a new year (admin)."""

from flask import Blueprint, jsonify

from myguro.database import get_db
from myguro.services import SchoolYearService
from myguro.web.security import current_user, json_body, role_required_api

bp = Blueprint("school_years", __name__)


def service():
    return SchoolYearService(get_db(), current_user())


@bp.get("/api/school-years")
@role_required_api("admin", "teacher", "student")
def api_list():
    return jsonify(service().overview())


@bp.put("/api/school-year")
@role_required_api("admin", "teacher", "student")
def api_view():
    return jsonify(service().view(json_body().get("id")))


@bp.post("/api/school-years")
@role_required_api("admin")
def api_start():
    return jsonify(service().start(json_body())), 201
