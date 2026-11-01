"""The holiday calendar: a page for admin, teachers and students; the admin adds local holidays."""

from flask import Blueprint, jsonify, render_template, request

from myguro.database import get_db
from myguro.config import school_today
from myguro.services.holidays import HolidayService
from myguro.web.security import current_user, json_body, role_required_api, role_required_page

bp = Blueprint("calendar", __name__)


def service():
    return HolidayService(get_db(), current_user())


@bp.get("/calendar")
@role_required_page("admin", "teacher", "student")
def page():
    return render_template("calendar.html", user=current_user())


@bp.get("/api/calendar")
@role_required_api("admin", "teacher", "student")
def api_year():
    return jsonify(service().year(request.args.get("year", school_today().year)))


@bp.post("/api/calendar/holidays")
@role_required_api("admin")
def api_add():
    return jsonify(id=service().add(json_body())), 201


@bp.put("/api/calendar/holidays/<int:holiday_id>")
@role_required_api("admin")
def api_update(holiday_id):
    service().update(holiday_id, json_body())
    return jsonify(ok=True)


@bp.delete("/api/calendar/holidays/<int:holiday_id>")
@role_required_api("admin")
def api_delete(holiday_id):
    service().delete(holiday_id)
    return jsonify(ok=True)
