"""Feedback: teachers and students rate MyGuro from 1 to 5; the admin reads the totals."""

from flask import Blueprint, jsonify, render_template, request

from myguro.database import get_db
from myguro.services import FeedbackService
from myguro.web.security import current_user, json_body, role_required_api, role_required_page

bp = Blueprint("feedback", __name__)


def service():
    return FeedbackService(get_db(), current_user())


@bp.get("/feedback")
@role_required_page("admin", "teacher", "student")
def page():
    """The same address for everyone: the admin sees the totals, teachers and students the rating form."""
    user = current_user()
    return render_template("feedback_results.html" if user["role"] == "admin" else "feedback.html", user=user)


@bp.get("/api/feedback")
@role_required_api("teacher", "student")
def api_mine():
    return jsonify(service().mine())


@bp.put("/api/feedback")
@role_required_api("teacher", "student")
def api_save():
    """{ratings: {"easy": 4, "overall": 5}}"""
    return jsonify(ratings=service().save(json_body()))


@bp.get("/api/feedback/summary")
@role_required_api("admin")
def api_summary():
    """?role=teacher|student for one group; no role = everyone."""
    return jsonify(service().summary(request.args.get("role", "")))
