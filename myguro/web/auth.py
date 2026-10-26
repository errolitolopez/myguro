"""Login, logout, change password."""

from flask import Blueprint, current_app, jsonify, redirect, render_template, session, url_for

from myguro.database import get_db
from myguro.services import AuthService
from myguro.web.security import client_address, current_user, json_body

bp = Blueprint("auth", __name__)


@bp.get("/")
def index():
    return redirect(url_for("dashboard.page" if current_user() else "auth.login_page"))


@bp.get("/login")
def login_page():
    if current_user():
        return redirect(url_for("dashboard.page"))
    return render_template("login.html")


@bp.get("/change-password")
def change_password_page():
    user = current_user()
    if user is None:
        return redirect(url_for("auth.login_page"))
    return render_template("change_password.html", user=user)


@bp.post("/api/login")
def api_login():
    data = json_body()
    user = AuthService(get_db()).login(data.get("username"), data.get("password"), client_address(),
                                       current_app.extensions["login_throttle"])
    session.clear()
    session["user_id"] = user["id"]
    return jsonify(ok=True, must_change_password=bool(user["must_change_password"]))


@bp.post("/api/logout")
def api_logout():
    user = current_user()
    if user is not None:
        AuthService(get_db(), user).logout()
    session.clear()
    return jsonify(ok=True)


@bp.post("/api/change-password")
def api_change_password():
    user = current_user()
    if user is None:
        return jsonify(error="Please log in."), 401
    data = json_body()
    AuthService(get_db(), user).change_password(data.get("current_password"), data.get("new_password"))
    return jsonify(ok=True)
