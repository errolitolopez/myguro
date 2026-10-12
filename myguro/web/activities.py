"""Teacher: activity sheets (editor), giving them to classes, and their settings."""

import io

from flask import Blueprint, jsonify, redirect, render_template, request, send_file, url_for

from myguro.database import get_db
from myguro.errors import ValidationError
from myguro.docx_files import read_docx_lines, sheet_template_docx_bytes
from myguro.imports import read_sheet_rows, sheet_template_xlsx_bytes
from myguro.services import ActivityService, AssignmentService
from myguro.web.security import current_user, json_body, role_required_api, role_required_page

bp = Blueprint("activities", __name__)


def service():
    return ActivityService(get_db(), current_user())


@bp.get("/activities")
@role_required_page("teacher")
def list_page():
    return render_template("activities.html", user=current_user())


@bp.get("/activities/import-template.xlsx")
@role_required_page("teacher")
def import_template():
    """The Excel file to fill in for importing an activity sheet."""
    return send_file(io.BytesIO(sheet_template_xlsx_bytes()), as_attachment=True,
                     download_name="myguro activity template.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@bp.get("/activities/import-template.docx")
@role_required_page("teacher")
def import_template_docx():
    """The Word file to fill in for importing an activity sheet."""
    return send_file(io.BytesIO(sheet_template_docx_bytes()), as_attachment=True,
                     download_name="myguro activity template.docx",
                     mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@bp.get("/activities/<int:activity_id>")
@role_required_page("teacher")
def editor_page(activity_id):
    if not service().exists(activity_id):
        return redirect(url_for("activities.list_page"))
    return render_template("activity_editor.html", user=current_user(), activity_id=activity_id)


@bp.get("/api/activities")
@role_required_api("teacher")
def api_list():
    return jsonify(activities=service().list())


@bp.post("/api/activities")
@role_required_api("teacher")
def api_create():
    return jsonify(activity=service().create(json_body())), 201


@bp.post("/api/activities/import")
@role_required_api("teacher")
def api_import():
    """Make a draft sheet from an uploaded .xlsx or .docx (form fields "file", "title", "subject").
    dry_run=1 only checks it."""
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        raise ValidationError("Choose an Excel (.xlsx) or Word (.docx) file.")
    data = {"title": request.form.get("title"), "subject": request.form.get("subject")}
    dry_run = request.form.get("dry_run") == "1"
    if upload.filename.lower().endswith(".docx"):
        return jsonify(service().import_docx_sheet(read_docx_lines(upload.read()), data, dry_run=dry_run))
    return jsonify(service().import_sheet(read_sheet_rows(upload.read()), data, dry_run=dry_run))


@bp.get("/api/activities/<int:activity_id>")
@role_required_api("teacher")
def api_get(activity_id):
    return jsonify(activity=service().get(activity_id))


@bp.put("/api/activities/<int:activity_id>")
@role_required_api("teacher")
def api_save(activity_id):
    return jsonify(activity=service().save(activity_id, json_body()))


@bp.delete("/api/activities/<int:activity_id>")
@role_required_api("teacher")
def api_delete(activity_id):
    service().delete(activity_id)
    return jsonify(ok=True)


@bp.post("/api/activities/<int:activity_id>/duplicate")
@role_required_api("teacher")
def api_duplicate(activity_id):
    return jsonify(activity=service().duplicate(activity_id)), 201


@bp.put("/api/activities/<int:activity_id>/settings")
@role_required_api("teacher")
def api_settings(activity_id):
    return jsonify(activity=service().update_settings(activity_id, json_body()))


@bp.get("/api/activities/<int:activity_id>/assignments")
@role_required_api("teacher")
def api_assignments(activity_id):
    return jsonify(AssignmentService(get_db(), current_user()).overview(activity_id))


@bp.put("/api/activities/<int:activity_id>/assignments")
@role_required_api("teacher")
def api_save_assignments(activity_id):
    return jsonify(AssignmentService(get_db(), current_user()).save(activity_id, json_body()))


@bp.get("/api/activities/<int:activity_id>/student-search")
@role_required_api("teacher")
def api_search_students(activity_id):
    """?q= name, username or section; ?grade= and ?section= filter exactly (?section= empty = no section)."""
    return jsonify(AssignmentService(get_db(), current_user()).search_students(
        activity_id, request.args.get("q", ""), request.args.get("grade"), request.args.get("section")))
