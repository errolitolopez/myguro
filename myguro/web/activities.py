"""Teacher: activity sheets (editor), giving them to classes, and their settings."""

from flask import Blueprint, jsonify, redirect, render_template, url_for

from myguro.database import get_db
from myguro.services import ActivityService, AssignmentService
from myguro.web.security import current_user, json_body, role_required_api, role_required_page

bp = Blueprint("activities", __name__)


def service():
    return ActivityService(get_db(), current_user())


@bp.get("/activities")
@role_required_page("teacher")
def list_page():
    return render_template("activities.html", user=current_user())


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
