"""Teacher: results of an assignment, scoring, another try, paper scores, exports."""

import io
import re

from flask import Blueprint, jsonify, redirect, render_template, request, send_file, url_for

from myguro.config import SCHOOL_TIMEZONE, school_now_text
from myguro.database import get_db
from myguro.exports import results_pdf_bytes, results_xlsx_bytes
from myguro.services import ResultsService
from myguro.web.security import current_user, json_body, role_required_api, role_required_page

bp = Blueprint("results", __name__)

EXPORTS = {
    "xlsx": (results_xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    "pdf": (results_pdf_bytes, "application/pdf"),
}


def service():
    return ResultsService(get_db(), current_user())


def file_name(title, class_name):
    """"Quiz 1 - Grade 9 - Rizal - Science": characters files can't have become "-"."""
    name = f"{title} - {class_name}".replace(" · ", " - ")
    return " ".join(re.sub(r'\s*[\\/:*?"<>|]+\s*', " - ", name).split())


@bp.get("/results/<int:assignment_id>")
@role_required_page("teacher")
def page(assignment_id):
    if not service().exists(assignment_id):
        return redirect(url_for("activities.list_page"))
    return render_template("results.html", user=current_user(), assignment_id=assignment_id)


@bp.get("/results/<int:assignment_id>/students/<int:student_id>")
@role_required_page("teacher")
def check_page(assignment_id, student_id):
    """Checking one student's answers, with a button to the next student."""
    if not service().exists(assignment_id):
        return redirect(url_for("activities.list_page"))
    return render_template("check.html", user=current_user(), assignment_id=assignment_id, student_id=student_id)


@bp.get("/results/<int:assignment_id>/export.<kind>")
@role_required_page("teacher")
def export(assignment_id, kind):
    """Download the results as Excel (.xlsx) or PDF."""
    results = service()
    if kind not in EXPORTS or not results.exists(assignment_id):
        return redirect(url_for("activities.list_page"))
    data = results.results(assignment_id)
    make, mimetype = EXPORTS[kind]
    content = make(data, current_user()["name"], school_now_text(), SCHOOL_TIMEZONE)
    name = file_name(data["assignment"]["title"], data["assignment"]["class_name"])
    return send_file(io.BytesIO(content), as_attachment=True, download_name=f"{name}.{kind}", mimetype=mimetype)


@bp.get("/api/results/to-check")
@role_required_api("teacher")
def api_to_check():
    return jsonify({"assignments": service().to_check(request.args.get("activity_id", type=int))})


@bp.get("/api/assignments/<int:assignment_id>/results")
@role_required_api("teacher")
def api_results(assignment_id):
    return jsonify(service().results(assignment_id))


@bp.get("/api/assignments/<int:assignment_id>/students/<int:student_id>")
@role_required_api("teacher")
def api_student(assignment_id, student_id):
    """?attempt= to see an earlier attempt."""
    return jsonify(service().student_result(assignment_id, student_id, request.args.get("attempt", type=int)))


@bp.put("/api/submissions/<int:submission_id>/points")
@role_required_api("teacher")
def api_points(submission_id):
    body = json_body()
    return jsonify(detail=service().set_points(submission_id, body.get("points"), body.get("feedback")))


@bp.put("/api/assignments/<int:assignment_id>/release")
@role_required_api("teacher")
def api_release(assignment_id):
    return jsonify(service().set_released(assignment_id, json_body().get("released")))


@bp.put("/api/assignments/<int:assignment_id>/open")
@role_required_api("teacher")
def api_open(assignment_id):
    """Open the assignment to its students ({"open": true}) or close it ({"open": false})."""
    return jsonify(service().set_opened(assignment_id, json_body().get("open")))


@bp.post("/api/assignments/<int:assignment_id>/students/<int:student_id>/reopen")
@role_required_api("teacher")
def api_reopen(assignment_id, student_id):
    return jsonify(service().reopen(assignment_id, student_id))


@bp.put("/api/assignments/<int:assignment_id>/students/<int:student_id>/excluded")
@role_required_api("teacher")
def api_excluded(assignment_id, student_id):
    """{excluded: true} for a student who is absent; {excluded: false} adds them back."""
    return jsonify(service().set_excluded(assignment_id, student_id, json_body().get("excluded")))


@bp.post("/api/assignments/<int:assignment_id>/students/<int:student_id>/paper")
@role_required_api("teacher")
def api_add_paper(assignment_id, student_id):
    return jsonify(service().add_paper(assignment_id, student_id, json_body()))


@bp.put("/api/submissions/<int:submission_id>/paper")
@role_required_api("teacher")
def api_edit_paper(submission_id):
    return jsonify(service().edit_paper(submission_id, json_body()))


@bp.delete("/api/submissions/<int:submission_id>/paper")
@role_required_api("teacher")
def api_delete_paper(submission_id):
    return jsonify(service().delete_paper(submission_id))
