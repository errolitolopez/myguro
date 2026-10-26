"""Supervisor and admin: the activity log page and its read-only API."""

from flask import Blueprint, jsonify, render_template, request

from myguro.database import get_db
from myguro.domain.log import CATEGORIES, LOG_ROLES, MAX_LOG_ENTRIES
from myguro.services import LogService
from myguro.web.security import current_user, role_required_api, role_required_page

bp = Blueprint("log", __name__)


def service():
    return LogService(get_db(), current_user())


@bp.get("/log")
@role_required_page("supervisor", "admin")
def page():
    return render_template("log.html", user=current_user(), categories=CATEGORIES, roles=LOG_ROLES,
                           max_entries=MAX_LOG_ENTRIES)


@bp.get("/api/log/chart")
@role_required_api("supervisor", "admin")
def api_chart():
    """?view=day|category|role and the same filters as the list. Counts only, no names."""
    args = request.args
    return jsonify(service().chart(
        args.get("view", "day"), query=args.get("q", ""), role=args.get("role", ""),
        category=args.get("category", ""), user_id=args.get("user_id", type=int),
        date_from=args.get("from", ""), date_to=args.get("to", ""),
    ))


@bp.get("/api/log")
@role_required_api("supervisor", "admin")
def api_list():
    """?q= search, ?role= ?category= ?user_id= ?from= ?to= (YYYY-MM-DD, school time), ?page= ?per_page=.
    Only GET exists: nothing can edit or delete an entry."""
    args = request.args
    return jsonify(service().list(
        query=args.get("q", ""), role=args.get("role", ""), category=args.get("category", ""),
        user_id=args.get("user_id", type=int), date_from=args.get("from", ""), date_to=args.get("to", ""),
        page=args.get("page", 1, type=int), per_page=args.get("per_page", 20, type=int),
    ))
