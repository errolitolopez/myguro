"""Navigation chatbot: a teacher asks where a page is and gets a link."""

from flask import Blueprint, jsonify

from myguro.database import get_db
from myguro.services import ChatService
from myguro.web.security import current_user, json_body, role_required_api

bp = Blueprint("chat", __name__)


@bp.post("/api/chat")
@role_required_api("teacher", "student", "admin", "supervisor")
def api_chat():
    """{message} -> {reply, link}. Every role may call it, but only a teacher gets an answer, and only
    while the admin has the chatbot on: for anyone else the service answers 404."""
    return jsonify(ChatService(get_db(), current_user()).ask(json_body()))
