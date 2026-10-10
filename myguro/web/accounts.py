"""Admin: Teachers and Students pages (the same page) and their API."""

import io

from flask import Blueprint, jsonify, render_template, request, send_file

from myguro.database import get_db
from myguro.errors import ValidationError
from myguro.imports import read_student_rows, template_xlsx_bytes
from myguro.services import AccountService
from myguro.web.security import current_user, json_body, role_required_api, role_required_page

bp = Blueprint("accounts", __name__)


def service():
    return AccountService(get_db(), current_user())


@bp.get("/teachers")
@role_required_page("admin")
def teachers_page():
    return render_template("users.html", user=current_user(), role="teacher")


@bp.get("/students")
@role_required_page("admin")
def students_page():
    return render_template("users.html", user=current_user(), role="student")


@bp.get("/api/users")
@role_required_api("admin")
def api_list():
    """?role=teacher (default) or student, ?q= search, ?grade= (empty = no grade), ?name= (full
    name, any order) and ?section= (advanced filters), ?page= and ?per_page= (20 by default)."""
    args = request.args
    return jsonify(service().list(
        args.get("role", "teacher"),
        query=args.get("q", ""),
        grade=args.get("grade") if "grade" in args else None,
        page=args.get("page", 1, type=int),
        per_page=args.get("per_page", 20, type=int),
        name=args.get("name", ""),
        section=args.get("section", ""),
    ))


@bp.post("/api/users")
@role_required_api("admin")
def api_create():
    user, temp_password = service().create(json_body())
    return jsonify(user=user, temp_password=temp_password), 201


@bp.put("/api/users/batch")
@role_required_api("admin")
def api_batch_update():
    """Grade and/or section of many students: {user_ids or match: {q, grade, name, section}, grade?, section?}."""
    return jsonify(updated=service().batch_update(json_body()))


@bp.put("/api/users/<int:user_id>")
@role_required_api("admin")
def api_update(user_id):
    user, temp_password = service().update(user_id, json_body())
    result = {"user": user}
    if temp_password:
        result["temp_password"] = temp_password
    return jsonify(result)


@bp.get("/students/import-template.xlsx")
@role_required_page("admin")
def import_template():
    """The Excel file to fill in for importing students."""
    return send_file(io.BytesIO(template_xlsx_bytes()), as_attachment=True,
                     download_name="myguro students template.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@bp.post("/api/users/import")
@role_required_api("admin")
def api_import_students():
    """Import students from an uploaded .xlsx (form field "file"). dry_run=1 only checks it."""
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        raise ValidationError("Choose an Excel file (.xlsx).")
    rows = read_student_rows(upload.read())
    return jsonify(service().import_students(rows, dry_run=request.form.get("dry_run") == "1"))

