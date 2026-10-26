"""Display settings page (theme and reading settings) for every role. Nothing is saved on the server:
the choices stay in the person's own browser (theme.js, reading.js)."""

from flask import Blueprint, render_template

from myguro.web.security import current_user, role_required_page

bp = Blueprint("display", __name__)


@bp.get("/display")
@role_required_page("admin", "teacher", "student", "supervisor")
def page():
    return render_template("display.html", user=current_user())
