"""Teacher: classes and the students in them."""

import io
import re

from flask import Blueprint, jsonify, redirect, render_template, request, send_file, url_for

from myguro.config import SCHOOL_TIMEZONE, school_now_text
from myguro.database import get_db
from myguro.exports import (attendance_pdf_bytes, attendance_xlsx_bytes, gradebook_pdf_bytes,
                            gradebook_xlsx_bytes, range_text)
from myguro.services import AttendanceService, ClassService, GradebookService
from myguro.services.presenters import class_title
from myguro.web.security import current_user, json_body, role_required_api, role_required_page

bp = Blueprint("classes", __name__)


GRADEBOOK_EXPORTS = {
    "xlsx": (gradebook_xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    "pdf": (gradebook_pdf_bytes, "application/pdf"),
}


ATTENDANCE_EXPORTS = {
    "xlsx": (attendance_xlsx_bytes, GRADEBOOK_EXPORTS["xlsx"][1]),
    "pdf": (attendance_pdf_bytes, GRADEBOOK_EXPORTS["pdf"][1]),
}


def service():
    return ClassService(get_db(), current_user())


@bp.get("/classes")
@role_required_page("teacher")
def list_page():
    return render_template("classes.html", user=current_user())


@bp.get("/classes/<int:class_id>")
@role_required_page("teacher")
def detail_page(class_id):
    if not service().exists(class_id):
        return redirect(url_for("classes.list_page"))
    return render_template("class.html", user=current_user(), class_id=class_id)


@bp.get("/classes/<int:class_id>/gradebook")
@role_required_page("teacher")
def gradebook_page(class_id):
    if not service().exists(class_id):
        return redirect(url_for("classes.list_page"))
    return render_template("gradebook.html", user=current_user(), class_id=class_id)


@bp.get("/classes/<int:class_id>/gradebook.<kind>")
@role_required_page("teacher")
def gradebook_export(class_id, kind):
    """Download the class gradebook as Excel (.xlsx) or PDF."""
    if kind not in GRADEBOOK_EXPORTS or not service().exists(class_id):
        return redirect(url_for("classes.list_page"))
    data = GradebookService(get_db(), current_user()).gradebook(class_id)
    make, mimetype = GRADEBOOK_EXPORTS[kind]
    content = make(data, current_user()["name"], school_now_text(), SCHOOL_TIMEZONE)
    # Characters files can't have become "-": "Gradebook - Grade 9 - Rizal - Science"
    name = re.sub(r'\s*[\\/:*?"<>|]+\s*', " - ", f"Gradebook - {class_title(data['class']['name'], data['class']['subject'])}")
    name = " ".join(name.replace(" · ", " - ").split())
    return send_file(io.BytesIO(content), as_attachment=True, download_name=f"{name}.{kind}", mimetype=mimetype)


@bp.get("/classes/<int:class_id>/attendance")
@role_required_page("teacher")
def attendance_page(class_id):
    if not service().exists(class_id):
        return redirect(url_for("classes.list_page"))
    return render_template("attendance.html", user=current_user(), class_id=class_id)


@bp.get("/classes/<int:class_id>/attendance.<kind>")
@role_required_page("teacher")
def attendance_export(class_id, kind):
    """Download the class's whole attendance record as Excel (.xlsx) or PDF."""
    if kind not in ATTENDANCE_EXPORTS or not service().exists(class_id):
        return redirect(url_for("classes.list_page"))
    # ?from= and ?to= (YYYY-MM-DD, both days included) keep only the days in between
    data = AttendanceService(get_db(), current_user()).record(class_id, request.args.get("from"), request.args.get("to"))
    make, mimetype = ATTENDANCE_EXPORTS[kind]
    content = make(data, current_user()["name"], school_now_text(), SCHOOL_TIMEZONE)
    name = re.sub(r'\s*[\\/:*?"<>|]+\s*', " - ", f"Attendance - {class_title(data['class']['name'], data['class']['subject'])}"
                  + (f" {range_text(data['range'])}" if data["range"]["from"] or data["range"]["to"] else ""))
    name = " ".join(name.replace(" · ", " - ").split())
    return send_file(io.BytesIO(content), as_attachment=True, download_name=f"{name}.{kind}", mimetype=mimetype)


@bp.get("/api/classes/<int:class_id>/attendance")
@role_required_api("teacher")
def api_attendance(class_id):
    """?date=YYYY-MM-DD (default today): the class's students with their mark for that day."""
    return jsonify(AttendanceService(get_db(), current_user()).sheet(class_id, request.args.get("date")))


@bp.put("/api/classes/<int:class_id>/attendance")
@role_required_api("teacher")
def api_save_attendance(class_id):
    """{day, marks: {student id: "present" | "late" | "absent" | "excused" | null}}"""
    return jsonify(AttendanceService(get_db(), current_user()).save(class_id, json_body()))


@bp.get("/api/classes/<int:class_id>/gradebook")
@role_required_api("teacher")
def api_gradebook(class_id):
    return jsonify(GradebookService(get_db(), current_user()).gradebook(class_id))


@bp.get("/api/classes")
@role_required_api("teacher")
def api_list():
    return jsonify(classes=service().list())


@bp.post("/api/classes")
@role_required_api("teacher")
def api_create():
    return jsonify(**{"class": service().create(json_body())}), 201


@bp.put("/api/classes/<int:class_id>")
@role_required_api("teacher")
def api_update(class_id):
    return jsonify(**{"class": service().update(class_id, json_body())})


@bp.get("/api/classes/<int:class_id>")
@role_required_api("teacher")
def api_detail(class_id):
    return jsonify(service().detail(class_id))


@bp.get("/api/classes/<int:class_id>/student-search")
@role_required_api("teacher")
def api_search_students(class_id):
    """?q= name, username or section; ?grade= and ?section= filter exactly (?section= empty = no section)."""
    return jsonify(service().search_students(class_id, request.args.get("q", ""), request.args.get("grade"),
                                             request.args.get("section")))


@bp.post("/api/classes/<int:class_id>/students")
@role_required_api("teacher")
def api_add_students(class_id):
    return jsonify(added=service().add_students(class_id, json_body())), 201


@bp.post("/api/classes/<int:class_id>/students/remove")
@role_required_api("teacher")
def api_remove_students(class_id):
    """{student_ids}: take several students out of the class at once."""
    return jsonify(removed=service().remove_students(class_id, json_body()))


@bp.delete("/api/classes/<int:class_id>/students/<int:student_id>")
@role_required_api("teacher")
def api_remove_student(class_id, student_id):
    service().remove_student(class_id, student_id)
    return jsonify(ok=True)
