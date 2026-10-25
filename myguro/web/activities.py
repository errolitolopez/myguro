"""Teacher: activity sheets (editor), giving them to classes, and their settings."""

import io
import re

from flask import Blueprint, jsonify, redirect, render_template, request, send_file, url_for

from myguro.database import get_db
from myguro.errors import ValidationError
from myguro.exports import sheet_pdf_bytes
from myguro.docx_files import read_docx_lines, sheet_docx_bytes, sheet_template_docx_bytes
from myguro.imports import sheet_xlsx_bytes
from myguro.services import ActivityService, AssignmentService
from myguro.web.security import current_user, json_body, role_required_api, role_required_page

bp = Blueprint("activities", __name__)


DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def service():
    return ActivityService(get_db(), current_user())


def file_name(title):
    """A title as a file name: characters files can't have become "-"."""
    return " ".join(re.sub(r'\s*[\\/:*?"<>|]+\s*', " - ", title).split())


@bp.get("/activities")
@role_required_page("teacher")
def list_page():
    return render_template("activities.html", user=current_user())


@bp.get("/activities/<int:activity_id>/print.pdf")
@role_required_page("teacher")
def print_pdf(activity_id):
    """The saved sheet as a PDF to print: the student copy, or with ?key=1 the copy with answers."""
    activities = service()
    if not activities.exists(activity_id):
        return redirect(url_for("activities.list_page"))
    activity = activities.get(activity_id)
    with_key = request.args.get("key") == "1"
    # Characters files can't have become "-": "Science Quiz 1 - answer key.pdf"
    name = file_name(activity["title"] + (" - answer key" if with_key else ""))
    content = sheet_pdf_bytes(activity, current_user()["name"], with_key)
    return send_file(io.BytesIO(content), download_name=f"{name}.pdf",
                     mimetype="application/pdf")  # opens in the browser, which has Print and Download


@bp.get("/activities/<int:activity_id>/export.<kind>")
@role_required_page("teacher")
def export(activity_id, kind):
    """Download the sheet with its answer key as Word (.docx), which the import reads so it can be
    imported again as a new activity, or as Excel (.xlsx)."""
    activities = service()
    if kind not in ("docx", "xlsx") or not activities.exists(activity_id):
        return redirect(url_for("activities.list_page"))
    activity = activities.get(activity_id)
    if kind == "docx":
        content, mimetype = sheet_docx_bytes(activity, current_user()["name"]), DOCX_TYPE
    else:
        content, mimetype = sheet_xlsx_bytes(activity), XLSX_TYPE
    return send_file(io.BytesIO(content), as_attachment=True, download_name=f"{file_name(activity['title'])}.{kind}",
                     mimetype=mimetype)


@bp.get("/activities/import-template.docx")
@role_required_page("teacher")
def import_template_docx():
    """The Word file to fill in for importing an activity sheet."""
    return send_file(io.BytesIO(sheet_template_docx_bytes()), as_attachment=True,
                     download_name="MyGURO activity template.docx",
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
    """?deleted=1 lists the sheets the teacher deleted (they can be restored)."""
    return jsonify(activities=service().list(deleted=request.args.get("deleted") == "1"))


@bp.post("/api/activities")
@role_required_api("teacher")
def api_create():
    return jsonify(activity=service().create(json_body())), 201


@bp.post("/api/activities/import")
@role_required_api("teacher")
def api_import():
    """Make a draft sheet from an uploaded .docx (form fields "file", "title", "subject").
    dry_run=1 only checks it."""
    upload = request.files.get("file")
    if upload is None or not upload.filename.lower().endswith(".docx"):
        raise ValidationError("Choose a Word (.docx) file.")
    data = {"title": request.form.get("title"), "subject": request.form.get("subject")}
    dry_run = request.form.get("dry_run") == "1"
    return jsonify(service().import_docx_sheet(read_docx_lines(upload.read()), data, dry_run=dry_run))


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
    """A sheet nobody has been given is deleted; an assigned one is archived (archived: true)."""
    return jsonify(ok=True, archived=service().delete(activity_id))


@bp.post("/api/activities/<int:activity_id>/restore")
@role_required_api("teacher")
def api_restore(activity_id):
    return jsonify(activity=service().restore(activity_id))


@bp.post("/api/activities/<int:activity_id>/duplicate")
@role_required_api("teacher")
def api_duplicate(activity_id):
    return jsonify(activity=service().duplicate(activity_id)), 201


@bp.put("/api/activities/<int:activity_id>/settings")
@role_required_api("teacher")
def api_settings(activity_id):
    return jsonify(activity=service().update_settings(activity_id, json_body()))


@bp.put("/api/activities/<int:activity_id>/published")
@role_required_api("teacher")
def api_published(activity_id):
    return jsonify(activity=service().set_published(activity_id, json_body().get("published")))


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
