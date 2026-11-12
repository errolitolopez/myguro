"""Teacher: the Students tab (their students) and one student's record."""

from flask import Blueprint, jsonify, render_template

from myguro.database import get_db
from myguro.services import StudentRecordService
from myguro.web.security import current_user, role_required_api, role_required_page

bp = Blueprint("students", __name__)


def service():
    return StudentRecordService(get_db(), current_user())


@bp.get("/my-students")
@role_required_page("teacher")
def list_page():
    return render_template("students.html", user=current_user())


@bp.get("/my-students/<int:student_id>")
@role_required_page("teacher")
def record_page(student_id):
    # The page asks the API, which answers 404 for a student who is not the teacher's; the page says so.
    return render_template("student_record.html", user=current_user(), student_id=student_id)


@bp.get("/api/my-students")
@role_required_api("teacher")
def api_list():
    return jsonify(students=service().students())


@bp.get("/api/my-students/<int:student_id>/record")
@role_required_api("teacher")
def api_record(student_id):
    return jsonify(service().record(student_id))
