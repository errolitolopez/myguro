"""Login, logout, change password."""

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for

from myguro.database import get_db
from myguro.domain import devices
from myguro.services import AuthService
from myguro.web.security import client_address, client_device, current_user, json_body

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
    # The browser's device id: kept in a cookie so the log can show when one device signs in as several people. A
    # browser with none (or a made-up one) gets a new random id.
    device_id = devices.clean_device_id(request.cookies.get(devices.COOKIE)) or devices.new_device_id()
    user = AuthService(get_db()).login(data.get("username"), data.get("password"), client_address(),
                                       current_app.extensions["login_throttle"], client_device(),
                                       devices.device_key(device_id))
    session.clear()
    session["user_id"] = user["id"]
    response = jsonify(ok=True, must_change_password=bool(user["must_change_password"]))
    response.set_cookie(devices.COOKIE, device_id, max_age=devices.COOKIE_MAX_AGE, httponly=True,
                        samesite="Lax", secure=request.is_secure)
    return response


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
