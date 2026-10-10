"""myguro: learning activity sheets for teachers and students.

Run with: flask --app app run --debug
"""

import os
import secrets
import time
from functools import wraps

from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

import db

app = Flask(__name__, instance_relative_config=True)

# The instance/ folder holds private files (database, secret key). It is not committed to git.
os.makedirs(app.instance_path, exist_ok=True)
app.config["DATABASE"] = os.environ.get(
    "MYGURO_DATABASE", os.path.join(app.instance_path, "myguro.db")
)
# No "remember me": the login ends when the browser is closed, since school computers are shared.
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


def load_secret_key():
    """The secret key signs the login cookie. Create one the first time and reuse it after."""
    path = os.path.join(app.instance_path, "secret_key")
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(secrets.token_hex(32))
    with open(path) as f:
        return f.read().strip()


app.secret_key = load_secret_key()
db.init_app(app)


# --- Login protection --------------------------------------------------------

# After too many wrong passwords, block that device + username for a while.
MAX_ATTEMPTS = 5
LOCK_SECONDS = 5 * 60
failed_logins = {}  # (ip address, username) -> {"count": wrong tries, "locked_until": timestamp}

MIN_PASSWORD_LENGTH = 8


def current_user():
    """The logged-in user's row, or None. Deactivated users count as logged out."""
    if "user" not in g:
        g.user = None
        user_id = session.get("user_id")
        if user_id is not None:
            user = db.get_db().execute(
                "SELECT * FROM users WHERE id = ? AND active = 1", (user_id,)
            ).fetchone()
            if user is None:
                session.clear()
            g.user = user
    return g.user


def login_required_page(view):
    """For HTML pages: send the user to the login page if not logged in,
    or to the change password page if they still have a temporary password."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None:
            return redirect(url_for("login_page"))
        if user["must_change_password"]:
            return redirect(url_for("change_password_page"))
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


# --- Pages -------------------------------------------------------------------

@app.get("/")
def index():
    return redirect(url_for("dashboard_page" if current_user() else "login_page"))


@app.get("/login")
def login_page():
    if current_user():
        return redirect(url_for("dashboard_page"))
    return render_template("login.html")


@app.get("/change-password")
def change_password_page():
    user = current_user()
    if user is None:
        return redirect(url_for("login_page"))
    return render_template("change_password.html", user=user)


@app.get("/dashboard")
@login_required_page
def dashboard_page():
    return render_template("dashboard.html", user=current_user())


# --- API: login --------------------------------------------------------------

@app.post("/api/login")
def api_login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    if not username or not password:
        return jsonify(error="Enter your username and password."), 400

    key = (request.remote_addr, username.lower())
    record = failed_logins.get(key, {"count": 0, "locked_until": 0})
    wait = int(record["locked_until"] - time.time())
    if wait > 0:
        return jsonify(error=f"Too many wrong tries. Try again in {wait // 60 + 1} min."), 429

    user = db.get_db().execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    if user is None or not check_password_hash(user["password_hash"], password):
        record["count"] += 1
        if record["count"] >= MAX_ATTEMPTS:
            record = {"count": 0, "locked_until": time.time() + LOCK_SECONDS}
        failed_logins[key] = record
        return jsonify(error="Wrong username or password."), 401
    if not user["active"]:
        return jsonify(error="This account is deactivated. Ask the admin."), 403

    failed_logins.pop(key, None)
    session.clear()
    session["user_id"] = user["id"]
    return jsonify(ok=True, must_change_password=bool(user["must_change_password"]))


@app.post("/api/logout")
def api_logout():
    session.clear()
    return jsonify(ok=True)


@app.post("/api/change-password")
def api_change_password():
    user = current_user()
    if user is None:
        return jsonify(error="Please log in."), 401

    data = request.get_json(silent=True) or {}
    current_password = str(data.get("current_password", ""))
    new_password = str(data.get("new_password", ""))

    if not check_password_hash(user["password_hash"], current_password):
        return jsonify(error="Current password is wrong."), 400
    if len(new_password) < MIN_PASSWORD_LENGTH:
        return jsonify(error=f"New password must be at least {MIN_PASSWORD_LENGTH} characters."), 400
    if new_password == current_password:
        return jsonify(error="New password must be different from the current one."), 400
    if new_password.lower() == user["username"].lower():
        return jsonify(error="New password can't be the same as your username."), 400

    database = db.get_db()
    database.execute(
        "UPDATE users SET password_hash = ?, must_change_password = 0 WHERE id = ?",
        (generate_password_hash(new_password), user["id"]),
    )
    database.commit()
    return jsonify(ok=True)


# --- API: dashboard ----------------------------------------------------------

def count(sql, params=()):
    return db.get_db().execute(sql, params).fetchone()[0]


@app.get("/api/dashboard")
@login_required_api
def api_dashboard():
    user = current_user()
    if user["role"] == "admin":
        return jsonify(
            role="admin",
            teachers=count("SELECT COUNT(*) FROM users WHERE role = 'teacher'"),
            active_teachers=count("SELECT COUNT(*) FROM users WHERE role = 'teacher' AND active = 1"),
            classes=count("SELECT COUNT(*) FROM classes"),
            students=count("SELECT COUNT(*) FROM students"),
            activities=count("SELECT COUNT(*) FROM activities"),
        )

    classes = db.get_db().execute(
        """
        SELECT c.id, c.name, c.code,
               (SELECT COUNT(*) FROM students s WHERE s.class_id = c.id) AS students,
               (SELECT COUNT(*) FROM activities a WHERE a.class_id = c.id) AS activities
        FROM classes c
        WHERE c.teacher_id = ?
        ORDER BY c.name
        """,
        (user["id"],),
    ).fetchall()
    mine = "SELECT id FROM classes WHERE teacher_id = ?"
    return jsonify(
        role="teacher",
        classes=[dict(row) for row in classes],
        students=count(f"SELECT COUNT(*) FROM students WHERE class_id IN ({mine})", (user["id"],)),
        published=count(
            f"SELECT COUNT(*) FROM activities WHERE status = 'published' AND class_id IN ({mine})",
            (user["id"],),
        ),
        drafts=count(
            f"SELECT COUNT(*) FROM activities WHERE status = 'draft' AND class_id IN ({mine})",
            (user["id"],),
        ),
        submissions=count(
            "SELECT COUNT(*) FROM submissions WHERE activity_id IN "
            f"(SELECT id FROM activities WHERE class_id IN ({mine}))",
            (user["id"],),
        ),
    )
