"""Who is logged in, and decorators that let only the right people open a page or API."""

import ipaddress
from functools import wraps

from flask import current_app, g, jsonify, redirect, request, session, url_for

from myguro.database import get_db
from myguro.repositories import UserRepository


def current_user():
    """The logged-in user's row, or None. Deactivated users count as logged out."""
    if "user" not in g:
        g.user = None
        user_id = session.get("user_id")
        if user_id is not None:
            user = UserRepository(get_db()).get_active(user_id)
            if user is None:
                session.clear()
            g.user = user
    return g.user


def client_address():
    """The address of the person's device, for the activity log and the wrong-password lock-out.
    Normally request.remote_addr. Behind a proxy (config TRUST_PROXY, from the MYGURO_TRUST_PROXY
    environment variable) that is the proxy's own address for everyone, so the address the proxy saw is
    read from the X-Real-IP header, else the last entry of X-Forwarded-For (the one our proxy added; the
    earlier ones can be made up by the visitor). Anything that is not a valid address falls back to
    remote_addr."""
    direct = request.remote_addr or ""
    if not current_app.config.get("TRUST_PROXY"):
        return direct
    candidate = request.headers.get("X-Real-IP", "").strip()
    if not candidate:
        candidate = request.headers.get("X-Forwarded-For", "").split(",")[-1].strip()
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return direct


def json_body():
    """The posted JSON object, or {} when there is none."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def login_required_page(view):
    """For HTML pages: send the user to the login page if not logged in,
    or to the change password page if they still have a temporary password."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None:
            return redirect(url_for("auth.login_page"))
        if user["must_change_password"]:
            return redirect(url_for("auth.change_password_page"))
        return view(*args, **kwargs)
    return wrapper


def login_required_api(view):
    """For API routes: answer 401 if not logged in, 403 if the password must be changed first."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None:
            return jsonify(error="Please log in."), 401
        if user["must_change_password"]:
            return jsonify(error="Please change your password first.", must_change_password=True), 403
        return view(*args, **kwargs)
    return wrapper


def role_required_page(*roles):
    """For HTML pages only some roles may open: others are sent back to their dashboard."""
    def decorator(view):
        @wraps(view)
        @login_required_page
        def wrapper(*args, **kwargs):
            if current_user()["role"] not in roles:
                return redirect(url_for("dashboard.page"))
            return view(*args, **kwargs)
        return wrapper
    return decorator


def role_required_api(*roles):
    """For API routes only some roles may use: others get 403."""
    def decorator(view):
        @wraps(view)
        @login_required_api
        def wrapper(*args, **kwargs):
            if current_user()["role"] not in roles:
                return jsonify(error="You don't have access to this."), 403
            return view(*args, **kwargs)
        return wrapper
    return decorator
