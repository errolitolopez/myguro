"""Time in / time out: the teacher's page (a beta, while the admin has it on) and the admin's records page."""

from flask import Blueprint, abort, jsonify, render_template, request

from myguro.database import get_db
from myguro.services import SettingsService, TimeClockService
from myguro.web.security import current_user, role_required_api, role_required_page

bp = Blueprint("time_clock", __name__)


def service():
    return TimeClockService(get_db(), current_user())


@bp.get("/time-clock")
@role_required_page("teacher")
def page():
    if not SettingsService(get_db(), current_user()).time_clock_enabled():
        abort(404)  # the beta is off: the page does not exist
    return render_template("time_clock.html", user=current_user())


@bp.get("/api/time-clock")
@role_required_api("teacher")
def api_mine():
    return jsonify(service().mine())


@bp.post("/api/time-clock/in")
@role_required_api("teacher")
def api_in():
    return jsonify(service().time_in())


@bp.post("/api/time-clock/out")
@role_required_api("teacher")
def api_out():
    return jsonify(service().time_out())


@bp.get("/time-records")
@role_required_page("admin")
def records_page():
    return render_template("time_records.html", user=current_user())


@bp.get("/api/time-records")
@role_required_api("admin")
def api_records():
    """?from= and ?to= (YYYY-MM-DD, school dates, both days included; default today), ?teacher_id= for one teacher."""
    args = request.args
    return jsonify(service().records(args.get("from", ""), args.get("to", ""), args.get("teacher_id", type=int)))
