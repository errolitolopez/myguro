"""myguro: learning activity sheets for teachers and students.

Run with: flask --app app run --debug
"""

import json
import os
import re
import secrets
import time
from functools import wraps

from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

import db
import seed

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
app.cli.add_command(seed.seed_command)


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


def role_required_page(*roles):
    """For HTML pages only some roles may open: others are sent back to their dashboard."""
    def decorator(view):
        @wraps(view)
        @login_required_page
        def wrapper(*args, **kwargs):
            if current_user()["role"] not in roles:
                return redirect(url_for("dashboard_page"))
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


@app.get("/teachers")
@role_required_page("admin")
def teachers_page():
    return render_template("users.html", user=current_user(), role="teacher")


@app.get("/students")
@role_required_page("admin")
def students_page():
    return render_template("users.html", user=current_user(), role="student")


@app.get("/activities")
@role_required_page("teacher")
def activities_page():
    return render_template("activities.html", user=current_user())


@app.get("/activities/<int:activity_id>")
@role_required_page("teacher")
def activity_editor_page(activity_id):
    if find_my_activity(activity_id) is None:
        return redirect(url_for("activities_page"))
    return render_template("activity_editor.html", user=current_user(), activity_id=activity_id)


@app.get("/classes")
@role_required_page("teacher")
def classes_page():
    return render_template("classes.html", user=current_user())


@app.get("/classes/<int:class_id>")
@role_required_page("teacher")
def class_page(class_id):
    if find_my_class(class_id) is None:
        return redirect(url_for("classes_page"))
    return render_template("class.html", user=current_user(), class_id=class_id)


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
            students=count("SELECT COUNT(*) FROM users WHERE role = 'student'"),
            activities=count("SELECT COUNT(*) FROM activities"),
        )

    if user["role"] == "student":
        classes = db.get_db().execute(
            """
            SELECT c.id, c.name, c.subject, t.name AS teacher,
                   (SELECT COUNT(*) FROM activity_classes ac JOIN activities a ON a.id = ac.activity_id
                    WHERE ac.class_id = c.id AND a.status = 'published') AS activities
            FROM class_students cs
            JOIN classes c ON c.id = cs.class_id
            JOIN users t ON t.id = c.teacher_id
            WHERE cs.student_id = ?
            ORDER BY c.name COLLATE NOCASE, c.subject COLLATE NOCASE
            """,
            (user["id"],),
        ).fetchall()
        return jsonify(
            role="student",
            classes=[dict(row) for row in classes],
            submitted=count("SELECT COUNT(*) FROM submissions WHERE student_id = ?", (user["id"],)),
        )

    mine = "SELECT id FROM classes WHERE teacher_id = ?"
    return jsonify(
        role="teacher",
        classes=my_classes(),
        students=count(
            f"SELECT COUNT(DISTINCT student_id) FROM class_students WHERE class_id IN ({mine})",
            (user["id"],),
        ),
        published=count(
            "SELECT COUNT(*) FROM activities WHERE status = 'published' AND teacher_id = ?", (user["id"],)
        ),
        drafts=count("SELECT COUNT(*) FROM activities WHERE status = 'draft' AND teacher_id = ?", (user["id"],)),
        submissions=count(
            "SELECT COUNT(*) FROM submissions WHERE activity_id IN "
            "(SELECT id FROM activities WHERE teacher_id = ?)",
            (user["id"],),
        ),
    )


# --- Accounts (shared by teachers and students) -------------------------------

USERNAME_PATTERN = re.compile(r"[a-z0-9._-]{3,30}")
MAX_NAME_LENGTH = 100
MAX_SECTION_LENGTH = 50
# Grade levels a student can have (or none). Shown as a dropdown so the values stay the same.
GRADES = ["Kinder"] + [f"Grade {number}" for number in range(1, 13)]
app.jinja_env.globals["GRADES"] = GRADES
# Temporary passwords leave out letters and digits that look alike (l, 1, o, 0).
TEMP_PASSWORD_LETTERS = "abcdefghjkmnpqrstuvwxyz23456789"


def make_temp_password():
    return "".join(secrets.choice(TEMP_PASSWORD_LETTERS) for _ in range(10))


def clean_name(value):
    return " ".join(str(value or "").split())


def name_error(name, label="Name"):
    """Why a name can't be used, or None when it's fine."""
    if not name:
        return f"{label} is required."
    if len(name) > MAX_NAME_LENGTH:
        return f"{label} can be at most {MAX_NAME_LENGTH} characters."
    return None


def user_json(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "username": row["username"],
        "active": bool(row["active"]),
        "must_change_password": bool(row["must_change_password"]),
        "created_at": row["created_at"],
        "grade": row["grade"],
        "section": row["section"],
    }


def grade_section_fields(data, student_id=None):
    """Clean grade + section from the posted data (students only, both optional).
    Returns (grade, section, error message or None).

    A section typed in other capitals than an existing one ("rizal" when "Rizal" exists)
    takes the existing spelling, so the same section isn't listed twice.
    student_id is the student being edited (their own section doesn't count).
    """
    grade = clean_name(data.get("grade"))
    section = clean_name(data.get("section"))
    if grade and grade not in GRADES:
        return grade, section, "Choose a grade from the list."
    if len(section) > MAX_SECTION_LENGTH:
        return grade, section, f"Section can be at most {MAX_SECTION_LENGTH} characters."
    if section:
        same = db.get_db().execute(
            "SELECT section FROM users WHERE role = 'student' AND section = ? COLLATE NOCASE "
            "AND id IS NOT ? LIMIT 1",
            (section, student_id),
        ).fetchone()
        if same:
            section = same["section"]
    return grade, section, None


def find_user(user_id, role):
    return db.get_db().execute(
        "SELECT * FROM users WHERE id = ? AND role = ?", (user_id, role)
    ).fetchone()


def create_account(role, data):
    """Create a teacher or student from the posted name, username and optional password.

    Returns (user row, temporary password, None), or (None, None, error message).
    The password is temporary: they must change it on first login. Only its hash is saved.
    The caller commits.
    """
    name = clean_name(data.get("name"))
    username = str(data.get("username", "")).strip().lower()
    password = str(data.get("password", "")) or make_temp_password()

    error = name_error(name)
    if error:
        return None, None, error
    grade, section = "", ""
    if role == "student":
        grade, section, error = grade_section_fields(data)
        if error:
            return None, None, error
    if not USERNAME_PATTERN.fullmatch(username):
        return None, None, ("Username must be 3 to 30 letters, numbers, dots, dashes or underscores, "
                            "with no spaces.")
    if len(password) < MIN_PASSWORD_LENGTH:
        return None, None, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."

    database = db.get_db()
    if database.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
        return None, None, f"The username \"{username}\" is already taken."

    cursor = database.execute(
        "INSERT INTO users (name, username, password_hash, role, must_change_password, grade, section) "
        "VALUES (?, ?, ?, ?, 1, ?, ?)",
        (name, username, generate_password_hash(password), role, grade, section),
    )
    return find_user(cursor.lastrowid, role), password, None


def reset_password(user_id):
    """Give an account a new temporary password and return it. The caller commits."""
    temp_password = make_temp_password()
    db.get_db().execute(
        "UPDATE users SET password_hash = ?, must_change_password = 1 WHERE id = ?",
        (generate_password_hash(temp_password), user_id),
    )
    return temp_password


# --- API: teacher and student accounts (admin only) ---------------------------

ACCOUNT_ROLES = ("teacher", "student")


def find_account(user_id):
    """A teacher or student account (never the admin)."""
    return db.get_db().execute(
        "SELECT * FROM users WHERE id = ? AND role IN ('teacher', 'student')", (user_id,)
    ).fetchone()


def account_json(row):
    """user_json plus how many classes the teacher teaches or the student is in."""
    result = user_json(row)
    result["role"] = row["role"]
    result["classes"] = db.get_db().execute(
        "SELECT COUNT(*) FROM classes WHERE teacher_id = ?" if row["role"] == "teacher"
        else "SELECT COUNT(*) FROM class_students WHERE student_id = ?",
        (row["id"],),
    ).fetchone()[0]
    return result


@app.get("/api/users")
@role_required_api("admin")
def api_list_users():
    """?role=teacher (default) or ?role=student"""
    role = request.args.get("role", "teacher")
    if role not in ACCOUNT_ROLES:
        return jsonify(error="Unknown role."), 400
    rows = db.get_db().execute(
        "SELECT * FROM users WHERE role = ? ORDER BY active DESC, name COLLATE NOCASE", (role,)
    ).fetchall()
    return jsonify(users=[account_json(row) for row in rows])


@app.post("/api/users")
@role_required_api("admin")
def api_create_user():
    """Create a teacher or student (role in the posted data).
    The password is sent back once so the admin can give it to them."""
    data = request.get_json(silent=True) or {}
    role = data.get("role", "teacher")
    if role not in ACCOUNT_ROLES:
        return jsonify(error="Unknown role."), 400
    user, temp_password, error = create_account(role, data)
    if error:
        return jsonify(error=error), 400
    db.get_db().commit()
    return jsonify(user=account_json(user), temp_password=temp_password), 201


@app.put("/api/users/<int:user_id>")
@role_required_api("admin")
def api_update_user(user_id):
    """Edit a teacher or student: name, grade + section (students), active (deactivate/activate),
    reset_password (gives a new temporary one)."""
    account = find_account(user_id)
    if account is None:
        return jsonify(error="Account not found."), 404

    data = request.get_json(silent=True) or {}
    database = db.get_db()
    temp_password = None

    if "name" in data:
        name = clean_name(data["name"])
        error = name_error(name)
        if error:
            return jsonify(error=error), 400
        database.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))

    if account["role"] == "student" and ("grade" in data or "section" in data):
        grade, section, error = grade_section_fields(
            {"grade": account["grade"], "section": account["section"], **data}, user_id
        )
        if error:
            return jsonify(error=error), 400
        database.execute("UPDATE users SET grade = ?, section = ? WHERE id = ?", (grade, section, user_id))

    if "active" in data:
        database.execute("UPDATE users SET active = ? WHERE id = ?", (1 if data["active"] else 0, user_id))

    if data.get("reset_password"):
        temp_password = reset_password(user_id)

    database.commit()
    result = {"user": account_json(find_account(user_id))}
    if temp_password:
        result["temp_password"] = temp_password
    return jsonify(result)


# --- API: classes and their students (teacher only) ----------------------------

def find_my_class(class_id):
    """The logged-in teacher's class, or None if it doesn't exist or belongs to another teacher."""
    return db.get_db().execute(
        "SELECT * FROM classes WHERE id = ? AND teacher_id = ?", (class_id, current_user()["id"])
    ).fetchone()


def class_json(row):
    return {"id": row["id"], "name": row["name"], "subject": row["subject"]}


def my_classes():
    rows = db.get_db().execute(
        """
        SELECT c.id, c.name, c.subject,
               (SELECT COUNT(*) FROM class_students cs WHERE cs.class_id = c.id) AS students,
               (SELECT COUNT(*) FROM activity_classes ac WHERE ac.class_id = c.id) AS activities
        FROM classes c
        WHERE c.teacher_id = ?
        ORDER BY c.name COLLATE NOCASE, c.subject COLLATE NOCASE
        """,
        (current_user()["id"],),
    ).fetchall()
    return [dict(row) for row in rows]


def class_fields(data):
    """Clean name + subject from the posted data. Returns (name, subject, error message or None)."""
    name = clean_name(data.get("name"))
    subject = clean_name(data.get("subject"))
    error = name_error(name, "Class name") or (
        "Subject can be at most 100 characters." if len(subject) > MAX_NAME_LENGTH else None
    )
    if error is None:
        same = db.get_db().execute(
            "SELECT id FROM classes WHERE teacher_id = ? AND name = ? COLLATE NOCASE "
            "AND subject = ? COLLATE NOCASE",
            (current_user()["id"], name, subject),
        ).fetchone()
        if same and same["id"] != data.get("id"):
            error = "You already have a class with this name and subject."
    return name, subject, error


@app.get("/api/classes")
@role_required_api("teacher")
def api_list_classes():
    return jsonify(classes=my_classes())


@app.post("/api/classes")
@role_required_api("teacher")
def api_create_class():
    name, subject, error = class_fields(request.get_json(silent=True) or {})
    if error:
        return jsonify(error=error), 400
    database = db.get_db()
    cursor = database.execute(
        "INSERT INTO classes (teacher_id, name, subject) VALUES (?, ?, ?)",
        (current_user()["id"], name, subject),
    )
    database.commit()
    return jsonify(**{"class": class_json(find_my_class(cursor.lastrowid))}), 201


@app.put("/api/classes/<int:class_id>")
@role_required_api("teacher")
def api_update_class(class_id):
    if find_my_class(class_id) is None:
        return jsonify(error="Class not found."), 404
    data = request.get_json(silent=True) or {}
    name, subject, error = class_fields({**data, "id": class_id})
    if error:
        return jsonify(error=error), 400
    database = db.get_db()
    database.execute("UPDATE classes SET name = ?, subject = ? WHERE id = ?", (name, subject, class_id))
    database.commit()
    return jsonify(**{"class": class_json(find_my_class(class_id))})


def class_students(class_id):
    rows = db.get_db().execute(
        """
        SELECT u.* FROM class_students cs JOIN users u ON u.id = cs.student_id
        WHERE cs.class_id = ?
        ORDER BY u.name COLLATE NOCASE
        """,
        (class_id,),
    ).fetchall()
    return [user_json(row) for row in rows]


def find_class_student(class_id, student_id):
    """The student, only if they are in this class."""
    return db.get_db().execute(
        "SELECT u.* FROM class_students cs JOIN users u ON u.id = cs.student_id "
        "WHERE cs.class_id = ? AND cs.student_id = ?",
        (class_id, student_id),
    ).fetchone()


@app.get("/api/classes/<int:class_id>")
@role_required_api("teacher")
def api_get_class(class_id):
    row = find_my_class(class_id)
    if row is None:
        return jsonify(error="Class not found."), 404
    return jsonify(**{"class": class_json(row)}, students=class_students(class_id))


# Enough for a whole section; the teacher can narrow the search for more.
MAX_SEARCH_RESULTS = 200


@app.get("/api/classes/<int:class_id>/student-search")
@role_required_api("teacher")
def api_search_students(class_id):
    """Search the school's student list (accounts are made by the admin) to add to this class.

    ?q= matches name, username or section; ?grade= and ?section= filter exactly
    (?section= with an empty value = students with no section). Deactivated students are left out.
    Also sends the grade + section pairs that exist, for the filter dropdowns.
    """
    if find_my_class(class_id) is None:
        return jsonify(error="Class not found."), 404
    query = clean_name(request.args.get("q"))
    pattern = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"

    sql = """
        SELECT u.*,
               EXISTS (SELECT 1 FROM class_students cs
                       WHERE cs.class_id = ? AND cs.student_id = u.id) AS in_class
        FROM users u
        WHERE u.role = 'student' AND u.active = 1
          AND (u.name LIKE ? ESCAPE '\\' OR u.username LIKE ? ESCAPE '\\' OR u.section LIKE ? ESCAPE '\\')
    """
    params = [class_id, pattern, pattern, pattern]
    if request.args.get("grade"):
        sql += " AND u.grade = ?"
        params.append(request.args["grade"])
    if "section" in request.args:
        sql += " AND u.section = ? COLLATE NOCASE"
        params.append(clean_name(request.args["section"]))
    sql += f" ORDER BY u.name COLLATE NOCASE LIMIT {MAX_SEARCH_RESULTS}"

    database = db.get_db()
    rows = database.execute(sql, params).fetchall()
    sections = database.execute(
        "SELECT DISTINCT grade, section FROM users WHERE role = 'student' AND active = 1 "
        "AND (grade != '' OR section != '') ORDER BY grade, section COLLATE NOCASE"
    ).fetchall()
    return jsonify(
        students=[{**user_json(row), "in_class": bool(row["in_class"])} for row in rows],
        more=len(rows) == MAX_SEARCH_RESULTS,
        sections=[{"grade": row["grade"], "section": row["section"]} for row in sections],
    )


@app.post("/api/classes/<int:class_id>/students")
@role_required_api("teacher")
def api_add_students(class_id):
    """Put students in this class: student_ids (a list, e.g. a whole section) or student_id.
    Students already in the class are skipped."""
    if find_my_class(class_id) is None:
        return jsonify(error="Class not found."), 404
    data = request.get_json(silent=True) or {}
    ids = data.get("student_ids", [data.get("student_id")])
    if not isinstance(ids, list) or not ids:
        return jsonify(error="No students to add."), 400

    database = db.get_db()
    added = []
    for student_id in ids:
        student = database.execute(
            "SELECT * FROM users WHERE id = ? AND role = 'student' AND active = 1", (student_id,)
        ).fetchone()
        if student is None:
            return jsonify(error="Student not found."), 404
        if find_class_student(class_id, student["id"]) is None:
            database.execute(
                "INSERT INTO class_students (class_id, student_id) VALUES (?, ?)", (class_id, student["id"])
            )
            added.append(user_json(student))
    database.commit()
    if not added and len(ids) == 1:
        return jsonify(error="This student is already in the class."), 400
    return jsonify(added=added), 201


@app.delete("/api/classes/<int:class_id>/students/<int:student_id>")
@role_required_api("teacher")
def api_remove_student(class_id, student_id):
    """Take a student out of this class. Their account and other classes are kept."""
    if find_my_class(class_id) is None or find_class_student(class_id, student_id) is None:
        return jsonify(error="Student not found in this class."), 404
    database = db.get_db()
    database.execute(
        "DELETE FROM class_students WHERE class_id = ? AND student_id = ?", (class_id, student_id)
    )
    database.commit()
    return jsonify(ok=True)


# --- API: learning activity sheets (teacher only) -----------------------------

MAX_TITLE_LENGTH = 150
MAX_SECTIONS = 50
MAX_DESCRIPTION_LENGTH = 20000


def find_my_activity(activity_id):
    """The logged-in teacher's activity sheet, or None if it doesn't exist or isn't theirs."""
    return db.get_db().execute(
        "SELECT * FROM activities WHERE id = ? AND teacher_id = ?", (activity_id, current_user()["id"])
    ).fetchone()


def activity_json(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "subject": row["subject"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def activity_title_fields(data):
    """Clean title + subject from the posted data. Returns (title, subject, error message or None)."""
    title = clean_name(data.get("title"))
    subject = clean_name(data.get("subject"))
    if not title:
        return title, subject, "Title is required."
    if len(title) > MAX_TITLE_LENGTH:
        return title, subject, f"Title can be at most {MAX_TITLE_LENGTH} characters."
    if len(subject) > MAX_NAME_LENGTH:
        return title, subject, f"Subject can be at most {MAX_NAME_LENGTH} characters."
    return title, subject, None


def clean_description(value):
    """Keep the teacher's line breaks and blank lines; only trim the ends (Windows line breaks become \\n)."""
    return str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()


SECTION_KINDS = ("text", "activity")
QUESTION_TYPES = ("multiple_choice", "true_false", "identification", "fill_blank", "short_answer")
MAX_QUESTIONS_PER_SECTION = 100
MAX_CHOICES = 6
MAX_POINTS = 100
MAX_ANSWER_LENGTH = 200
BLANK = re.compile(r"_{3,}")  # ___ (three or more underscores) marks a blank


def clean_answers(values, where):
    """A list of accepted answers ("Taoism", "Daoism"), cleaned. Returns (list, error or None)."""
    if not isinstance(values, list):
        return [], f"{where}: the answer is not valid."
    answers = [clean_name(value) for value in values if clean_name(value)]
    if not answers:
        return [], f"{where}: type the correct answer."
    if any(len(answer) > MAX_ANSWER_LENGTH for answer in answers):
        return [], f"{where}: an answer can be at most {MAX_ANSWER_LENGTH} characters."
    return answers, None


def question_fields(question, where):
    """Clean one posted question. Returns (dict to save, error message or None).

    where is like "Section 3, question 2", for error messages.
    """
    if not isinstance(question, dict):
        return None, f"{where} is not valid."
    kind = question.get("type")
    if kind not in QUESTION_TYPES:
        return None, f"{where}: unknown question type."
    prompt = clean_description(question.get("prompt"))
    if not prompt:
        return None, f"{where}: type the question."
    if len(prompt) > MAX_DESCRIPTION_LENGTH:
        return None, f"{where}: the question is too long."
    points = question.get("points", 1)
    if not isinstance(points, int) or isinstance(points, bool) or not 1 <= points <= MAX_POINTS:
        return None, f"{where}: points must be a whole number from 1 to {MAX_POINTS}."

    choices = None
    if kind == "multiple_choice":
        choices = question.get("choices")
        if not isinstance(choices, list):
            return None, f"{where}: the choices are not valid."
        choices = [clean_name(choice) for choice in choices]
        if len(choices) < 2 or len(choices) > MAX_CHOICES:
            return None, f"{where}: give 2 to {MAX_CHOICES} choices."
        if not all(choices):
            return None, f"{where}: a choice is empty. Type it or remove it."
        if any(len(choice) > MAX_ANSWER_LENGTH for choice in choices):
            return None, f"{where}: a choice can be at most {MAX_ANSWER_LENGTH} characters."
        answer = question.get("answer")
        if not isinstance(answer, int) or isinstance(answer, bool) or not 0 <= answer < len(choices):
            return None, f"{where}: choose the correct answer."
    elif kind == "true_false":
        answer = question.get("answer")
        if not isinstance(answer, bool):
            return None, f"{where}: choose True or False as the correct answer."
    elif kind == "identification":
        answer, error = clean_answers(question.get("answer"), where)
        if error:
            return None, error
    elif kind == "short_answer":
        # No right answer: the student writes their own and the teacher scores it.
        # The answer is an optional guide for checking (key points), seen only by the teacher.
        answer = clean_description(question.get("answer"))
        if len(answer) > MAX_DESCRIPTION_LENGTH:
            return None, f"{where}: the guide for checking is too long."
    else:  # fill_blank
        blanks = len(BLANK.findall(prompt))
        if blanks == 0:
            return None, f"{where}: put ___ (three underscores) where the blank goes."
        answer = question.get("answer")
        if not isinstance(answer, list) or len(answer) != blanks:
            return None, f"{where}: type the answer for each blank."
        cleaned = []
        for number, values in enumerate(answer, start=1):
            values, error = clean_answers(values, f"{where}, blank {number}")
            if error:
                return None, error
            cleaned.append(values)
        answer = cleaned

    return {
        "id": question.get("id"),
        "type": kind,
        "prompt": prompt,
        "choices": choices,
        "answer": answer,
        "points": points,
    }, None


def section_fields(sections):
    """Clean the posted list of sections, each with its questions.
    Returns (list of dicts to save, error message or None)."""
    if not isinstance(sections, list):
        return [], "Sections must be a list."
    if len(sections) > MAX_SECTIONS:
        return [], f"An activity can have at most {MAX_SECTIONS} sections."
    cleaned = []
    for number, section in enumerate(sections, start=1):
        if not isinstance(section, dict):
            return [], f"Section {number} is not valid."
        kind = section.get("kind", "text")
        if kind not in SECTION_KINDS:
            return [], f"Section {number}: unknown kind of section."
        title = clean_name(section.get("title"))
        description = clean_description(section.get("description"))
        if len(title) > MAX_TITLE_LENGTH:
            return [], f"Section {number}: the title can be at most {MAX_TITLE_LENGTH} characters."
        if len(description) > MAX_DESCRIPTION_LENGTH:
            return [], f"Section {number}: the text can be at most {MAX_DESCRIPTION_LENGTH} characters."

        questions = []
        if kind == "text":
            if not title and not description:
                return [], f"Section {number} is empty. Type a title or description, or delete it."
        else:
            posted = section.get("questions", [])
            if not isinstance(posted, list):
                return [], f"Section {number}: the questions are not valid."
            if not posted:
                return [], f"Section {number} is an activity with no questions. Add a question, or delete it."
            if len(posted) > MAX_QUESTIONS_PER_SECTION:
                return [], f"Section {number}: at most {MAX_QUESTIONS_PER_SECTION} questions."
            for question_number, question in enumerate(posted, start=1):
                question, error = question_fields(question, f"Section {number}, question {question_number}")
                if error:
                    return [], error
                questions.append(question)

        cleaned.append({
            "id": section.get("id"),
            "kind": kind,
            "title": title,
            "description": description,
            "questions": questions,
        })
    return cleaned, None


def save_sections(activity_id, sections):
    """Save cleaned sections and questions in order. Ones with the id of an existing section or
    question of this activity are updated (so students' answers keep pointing to them), new ones
    are added, and ones no longer in the list are deleted. The caller commits."""
    database = db.get_db()
    old_sections = {row["id"] for row in database.execute(
        "SELECT id FROM activity_sections WHERE activity_id = ?", (activity_id,))}
    old_questions = {row["id"] for row in database.execute(
        "SELECT id FROM questions WHERE activity_id = ?", (activity_id,))}
    kept_sections, kept_questions = set(), set()

    for position, section in enumerate(sections):
        values = (section["kind"], section["title"], section["description"], position)
        if section["id"] in old_sections and section["id"] not in kept_sections:
            section_id = section["id"]
            database.execute(
                "UPDATE activity_sections SET kind = ?, title = ?, description = ?, position = ? WHERE id = ?",
                (*values, section_id),
            )
        else:
            section_id = database.execute(
                "INSERT INTO activity_sections (kind, title, description, position, activity_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (*values, activity_id),
            ).lastrowid
        kept_sections.add(section_id)

        for question_position, question in enumerate(section["questions"]):
            values = (
                section_id, question_position, question["type"], question["prompt"],
                json.dumps(question["choices"]) if question["choices"] is not None else None,
                json.dumps(question["answer"]), question["points"],
            )
            if question["id"] in old_questions and question["id"] not in kept_questions:
                question_id = question["id"]
                database.execute(
                    "UPDATE questions SET section_id = ?, position = ?, type = ?, prompt = ?, "
                    "choices = ?, answer = ?, points = ? WHERE id = ?",
                    (*values, question_id),
                )
            else:
                question_id = database.execute(
                    "INSERT INTO questions (section_id, position, type, prompt, choices, answer, points, "
                    "activity_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (*values, activity_id),
                ).lastrowid
            kept_questions.add(question_id)

    for question_id in old_questions - kept_questions:
        database.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    for section_id in old_sections - kept_sections:
        database.execute("DELETE FROM activity_sections WHERE id = ?", (section_id,))


def question_json(row):
    return {
        "id": row["id"],
        "type": row["type"],
        "prompt": row["prompt"],
        "choices": json.loads(row["choices"]) if row["choices"] else None,
        "answer": json.loads(row["answer"]),
        "points": row["points"],
    }


def activity_sections(activity_id):
    """The sections of an activity in order, each with its questions (with the answer key:
    for the teacher only)."""
    database = db.get_db()
    sections = [dict(row) for row in database.execute(
        "SELECT id, kind, title, description FROM activity_sections WHERE activity_id = ? ORDER BY position",
        (activity_id,),
    )]
    questions = database.execute(
        "SELECT * FROM questions WHERE activity_id = ? ORDER BY position", (activity_id,)
    ).fetchall()
    for section in sections:
        section["questions"] = [question_json(row) for row in questions if row["section_id"] == section["id"]]
    return sections


@app.get("/api/activities")
@role_required_api("teacher")
def api_list_activities():
    rows = db.get_db().execute(
        """
        SELECT a.*,
               (SELECT COUNT(*) FROM activity_sections s WHERE s.activity_id = a.id) AS sections,
               (SELECT COUNT(*) FROM questions q WHERE q.activity_id = a.id) AS questions
        FROM activities a
        WHERE a.teacher_id = ?
        ORDER BY a.updated_at DESC, a.id DESC
        """,
        (current_user()["id"],),
    ).fetchall()
    return jsonify(activities=[
        {**activity_json(row), "sections": row["sections"], "questions": row["questions"]} for row in rows
    ])


@app.post("/api/activities")
@role_required_api("teacher")
def api_create_activity():
    """Start a new activity sheet (a draft) with its title and subject; sections are added in the editor."""
    title, subject, error = activity_title_fields(request.get_json(silent=True) or {})
    if error:
        return jsonify(error=error), 400
    database = db.get_db()
    cursor = database.execute(
        "INSERT INTO activities (teacher_id, title, subject) VALUES (?, ?, ?)",
        (current_user()["id"], title, subject),
    )
    database.commit()
    return jsonify(activity=activity_json(find_my_activity(cursor.lastrowid))), 201


@app.get("/api/activities/<int:activity_id>")
@role_required_api("teacher")
def api_get_activity(activity_id):
    row = find_my_activity(activity_id)
    if row is None:
        return jsonify(error="Activity not found."), 404
    return jsonify(activity={**activity_json(row), "sections": activity_sections(activity_id)})


@app.put("/api/activities/<int:activity_id>")
@role_required_api("teacher")
def api_update_activity(activity_id):
    """Save the title, subject, and the sections with their questions, in the posted order."""
    if find_my_activity(activity_id) is None:
        return jsonify(error="Activity not found."), 404
    data = request.get_json(silent=True) or {}
    title, subject, error = activity_title_fields(data)
    if error:
        return jsonify(error=error), 400
    sections, error = section_fields(data.get("sections", []))
    if error:
        return jsonify(error=error), 400

    database = db.get_db()
    database.execute(
        "UPDATE activities SET title = ?, subject = ?, updated_at = datetime('now') WHERE id = ?",
        (title, subject, activity_id),
    )
    save_sections(activity_id, sections)
    database.commit()
    return jsonify(activity={**activity_json(find_my_activity(activity_id)),
                             "sections": activity_sections(activity_id)})


@app.delete("/api/activities/<int:activity_id>")
@role_required_api("teacher")
def api_delete_activity(activity_id):
    """Delete an activity sheet that no class has been given yet."""
    if find_my_activity(activity_id) is None:
        return jsonify(error="Activity not found."), 404
    database = db.get_db()
    if database.execute("SELECT 1 FROM activity_classes WHERE activity_id = ?", (activity_id,)).fetchone():
        return jsonify(error="This activity was already given to a class, so it can't be deleted."), 400
    database.execute("DELETE FROM questions WHERE activity_id = ?", (activity_id,))
    database.execute("DELETE FROM activity_sections WHERE activity_id = ?", (activity_id,))
    database.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
    database.commit()
    return jsonify(ok=True)

