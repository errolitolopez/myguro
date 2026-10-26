"""The schedule generator: the admin's setup and timetable pages, and each teacher's own schedule."""

from flask import Blueprint, jsonify, render_template, request

from myguro.database import get_db
from myguro.services import ScheduleService
from myguro.web.security import current_user, json_body, role_required_api, role_required_page

bp = Blueprint("schedule", __name__)


def service():
    return ScheduleService(get_db(), current_user())


@bp.get("/schedule")
@role_required_page("admin")
def admin_page():
    return render_template("schedule.html", user=current_user())


@bp.get("/my-schedule")
@role_required_page("teacher")
def my_page():
    return render_template("my_schedule.html", user=current_user())


@bp.get("/api/schedule")
@role_required_api("admin")
def api_overview():
    return jsonify(service().overview())


@bp.put("/api/schedule/rules")
@role_required_api("admin")
def api_rules():
    return jsonify(rules=service().set_rules(json_body()))


@bp.post("/api/schedule/sections")
@role_required_api("admin")
def api_add_section():
    return jsonify(id=service().add_section(json_body())), 201


@bp.put("/api/schedule/sections/<int:section_id>")
@role_required_api("admin")
def api_update_section(section_id):
    service().update_section(section_id, json_body())
    return jsonify(ok=True)


@bp.delete("/api/schedule/sections/<int:section_id>")
@role_required_api("admin")
def api_delete_section(section_id):
    service().delete_section(section_id)
    return jsonify(ok=True)


@bp.post("/api/schedule/teachers")
@role_required_api("admin")
def api_add_teacher():
    return jsonify(id=service().add_teacher(json_body())), 201


@bp.put("/api/schedule/teachers/<int:teacher_id>")
@role_required_api("admin")
def api_update_teacher(teacher_id):
    service().update_teacher(teacher_id, json_body())
    return jsonify(ok=True)


@bp.delete("/api/schedule/teachers/<int:teacher_id>")
@role_required_api("admin")
def api_delete_teacher(teacher_id):
    service().delete_teacher(teacher_id)
    return jsonify(ok=True)


@bp.put("/api/schedule/assignments")
@role_required_api("admin")
def api_set_assignment():
    """{section_id, subject, teacher_id, per_week}: add the subject to the section or change it."""
    return jsonify(id=service().set_assignment(json_body()))


@bp.delete("/api/schedule/assignments/<int:assignment_id>")
@role_required_api("admin")
def api_delete_assignment(assignment_id):
    service().delete_assignment(assignment_id)
    return jsonify(ok=True)


@bp.post("/api/schedule/generate")
@role_required_api("admin")
def api_generate():
    return jsonify(service().generate(json_body()))


@bp.post("/api/schedule/swap")
@role_required_api("admin")
def api_swap():
    return jsonify(service().swap(json_body()))


@bp.put("/api/schedule/published")
@role_required_api("admin")
def api_published():
    return jsonify(published=service().set_published(json_body()))


@bp.get("/api/schedule/sections/<int:section_id>/grid")
@role_required_api("admin")
def api_section_grid(section_id):
    return jsonify(service().section_grid(section_id))


@bp.get("/api/schedule/teachers/<int:teacher_id>/grid")
@role_required_api("admin")
def api_teacher_grid(teacher_id):
    return jsonify(service().teacher_grid(teacher_id))


@bp.get("/api/my-schedule")
@role_required_api("teacher")
def api_my_schedule():
    return jsonify(service().my_schedule())
