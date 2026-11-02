"""The bell: a student's own notifications."""

from flask import Blueprint, jsonify

from myguro.database import get_db
from myguro.services import NotificationService
from myguro.web.security import current_user, role_required_api

bp = Blueprint("notifications", __name__)


def service():
    return NotificationService(get_db(), current_user())


@bp.get("/api/notifications")
@role_required_api("student")
def api_list():
    return jsonify(service().mine())


@bp.post("/api/notifications/<int:note_id>/read")
@role_required_api("student")
def api_read(note_id):
    service().read(note_id)
    return jsonify(ok=True)


@bp.post("/api/notifications/read-all")
@role_required_api("student")
def api_read_all():
    service().read_all()
    return jsonify(ok=True)
