"""The old /display address: Display moved into the Settings page, so old bookmarks and links still work."""

from flask import Blueprint, redirect, url_for

from myguro.web.security import role_required_page

bp = Blueprint("display", __name__)


@bp.get("/display")
@role_required_page("admin", "teacher", "student", "supervisor")
def page():
    return redirect(url_for("settings.page") + "#appearance")
