"""Teacher: classes and the students in them."""

from flask import Blueprint, jsonify, redirect, render_template, request, url_for

from myguro.database import get_db
from myguro.services import ClassService
from myguro.web.security import current_user, json_body, role_required_api, role_required_page

bp = Blueprint("classes", __name__)


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
