"""Admin: Teachers and Students pages (the same page) and their API."""

from flask import Blueprint, jsonify, render_template, request

from myguro.database import get_db
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
    """?role=teacher (default) or ?role=student"""
    return jsonify(users=service().list(request.args.get("role", "teacher")))


@bp.post("/api/users")
@role_required_api("admin")
def api_create():
    user, temp_password = service().create(json_body())
    return jsonify(user=user, temp_password=temp_password), 201


@bp.put("/api/users/<int:user_id>")
@role_required_api("admin")
def api_update(user_id):
    user, temp_password = service().update(user_id, json_body())
    result = {"user": user}
    if temp_password:
        result["temp_password"] = temp_password
    return jsonify(result)
