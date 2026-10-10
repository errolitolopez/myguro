"""Students: My activities and answering."""

from flask import Blueprint, jsonify, redirect, render_template, url_for

from myguro.config import school_today
from myguro.database import get_db
from myguro.services import StudentWorkService
from myguro.web.security import current_user, json_body, role_required_api, role_required_page

bp = Blueprint("student", __name__)


def service():
    return StudentWorkService(get_db(), current_user())


@bp.get("/my-activities")
@role_required_page("student")
def activities_page():
    return render_template("my_activities.html", user=current_user())


@bp.get("/my-activities/<int:assignment_id>")
@role_required_page("student")
def answer_page(assignment_id):
    if not service().exists(assignment_id):
        return redirect(url_for("student.activities_page"))
    return render_template("answer.html", user=current_user(), assignment_id=assignment_id)


@bp.get("/api/my-activities")
@role_required_api("student")
def api_list():
    return jsonify(activities=service().list(), today=school_today().isoformat())


@bp.get("/api/my-activities/<int:assignment_id>")
@role_required_api("student")
def api_detail(assignment_id):
    return jsonify(activity=service().detail(assignment_id))


@bp.put("/api/my-activities/<int:assignment_id>/answers")
@role_required_api("student")
def api_save_answers(assignment_id):
    service().save(assignment_id, json_body().get("answers", {}))
    return jsonify(ok=True)


@bp.post("/api/my-activities/<int:assignment_id>/submit")
@role_required_api("student")
def api_submit(assignment_id):
    return jsonify(activity=service().submit(assignment_id, json_body().get("answers", {})))


@bp.post("/api/my-activities/<int:assignment_id>/retry")
@role_required_api("student")
def api_retry(assignment_id):
    return jsonify(activity=service().retry(assignment_id))
