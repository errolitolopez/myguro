"""The calendar: a public page (anyone may read the holidays, without logging in); the admin adds local holidays and school events."""

from datetime import date

from flask import Blueprint, abort, jsonify, render_template, request

from myguro.database import get_db
from myguro.config import GENERATED_BY, school_today
from myguro.domain.holidays import MAX_YEAR, MIN_YEAR
from myguro.services.holidays import HolidayService
from myguro.services.school_events import SchoolEventService
from myguro.web.security import (
    current_user, json_body, optional_login_api, optional_login_page, role_required_api,
)

bp = Blueprint("calendar", __name__)


def service():
    return HolidayService(get_db(), current_user())


def event_service():
    return SchoolEventService(get_db(), current_user())


# The month or day on screen is in the address, so a person can share the link to it. calendar.js reads the address.
@bp.get("/calendar")
@bp.get("/calendar/<int:year>/<int:month>")
@bp.get("/calendar/<int:year>/<int:month>/<int:day>")
@optional_login_page
def page(year=None, month=None, day=None):
    if year is not None:
        try:
            date(year, month, day or 1)
        except ValueError:
            abort(404)
        if not MIN_YEAR <= year <= MAX_YEAR:
            abort(404)
    return render_template("calendar.html", user=current_user(), min_year=MIN_YEAR, max_year=MAX_YEAR,
                           generated_by=GENERATED_BY, events_hidden=service().events_hidden())


@bp.get("/api/calendar")
@optional_login_api
def api_year():
    return jsonify(service().year(request.args.get("year", school_today().year)))


@bp.get("/api/calendar/upcoming")
@optional_login_api
def api_upcoming():
    return jsonify(service().upcoming())


@bp.get("/api/calendar/search")
@optional_login_api
def api_search():
    return jsonify(service().search(request.args.get("q", "")))


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


@bp.post("/api/calendar/events")
@role_required_api("admin")
def api_add_event():
    return jsonify(id=event_service().add(json_body())), 201


@bp.put("/api/calendar/events/<int:event_id>")
@role_required_api("admin")
def api_update_event(event_id):
    event_service().update(event_id, json_body())
    return jsonify(ok=True)


@bp.delete("/api/calendar/events/<int:event_id>")
@role_required_api("admin")
def api_delete_event(event_id):
    event_service().delete(event_id)
    return jsonify(ok=True)
