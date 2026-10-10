"""myguro: learning activity sheets for teachers and students.

Run with: flask --app app run --debug
"""

import io
import json
import os
import re
import secrets
import time
from datetime import date, datetime
from functools import wraps
from zoneinfo import ZoneInfo

from flask import Flask, g, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

import db
import seed
from results_export import results_pdf_bytes, results_xlsx_bytes

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


@app.get("/my-activities")
@role_required_page("student")
def my_activities_page():
    return render_template("my_activities.html", user=current_user())


@app.get("/my-activities/<int:assignment_id>")
@role_required_page("student")
def answer_page(assignment_id):
    if find_student_assignment(assignment_id) is None:
        return redirect(url_for("my_activities_page"))
    return render_template("answer.html", user=current_user(), assignment_id=assignment_id)


@app.get("/results/<int:assignment_id>")
@role_required_page("teacher")
def results_page(assignment_id):
    if find_my_assignment(assignment_id) is None:
        return redirect(url_for("activities_page"))
    return render_template("results.html", user=current_user(), assignment_id=assignment_id)


@app.get("/results/<int:assignment_id>/export.<kind>")
@role_required_page("teacher")
def export_results(assignment_id, kind):
    """Download the results as Excel (.xlsx) or PDF."""
    assignment = find_my_assignment(assignment_id)
    if assignment is None or kind not in ("xlsx", "pdf"):
        return redirect(url_for("activities_page"))
    data = results_data(assignment)
    exported_at = datetime.now(SCHOOL_TIMEZONE).strftime("%Y-%m-%d %H:%M")
    make = results_xlsx_bytes if kind == "xlsx" else results_pdf_bytes
    content = make(data, current_user()["name"], exported_at, SCHOOL_TIMEZONE)
    # "Quiz 1 - Grade 9 - Rizal - Science.xlsx": characters files can't have become "-"
    name = f"{data['assignment']['title']} - {data['assignment']['class_name']}".replace(" · ", " - ")
    name = " ".join(re.sub(r'\s*[\\/:*?"<>|]+\s*', " - ", name).split())
    return send_file(
        io.BytesIO(content),
        as_attachment=True,
        download_name=f"{name}.{kind}",
        mimetype="application/pdf" if kind == "pdf"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


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
                   (SELECT COUNT(*) FROM assignments asg
                    WHERE asg.class_id = c.id AND (asg.everyone = 1 OR EXISTS (
                        SELECT 1 FROM assignment_students s
                        WHERE s.assignment_id = asg.id AND s.student_id = cs.student_id))) AS activities
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
            submitted=count(
                "SELECT COUNT(DISTINCT assignment_id) FROM submissions "
                "WHERE student_id = ? AND submitted_at IS NOT NULL",
                (user["id"],),
            ),
            to_do=sum(1 for item in student_assignments(user["id"]) if item["score"] is None),
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
            "SELECT COUNT(*) FROM activities a WHERE teacher_id = ? "
            "AND EXISTS (SELECT 1 FROM assignments WHERE activity_id = a.id)",
            (user["id"],),
        ),
        drafts=count(
            "SELECT COUNT(*) FROM activities a WHERE teacher_id = ? "
            "AND NOT EXISTS (SELECT 1 FROM assignments WHERE activity_id = a.id)",
            (user["id"],),
        ),
        # Students who submitted (each student once per assignment, however many attempts)
        submissions=count(
            "SELECT COUNT(*) FROM (SELECT DISTINCT assignment_id, student_id FROM submissions "
            "WHERE submitted_at IS NOT NULL AND assignment_id IN "
            "(SELECT asg.id FROM assignments asg JOIN activities a ON a.id = asg.activity_id "
            "WHERE a.teacher_id = ?))",
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
               (SELECT COUNT(*) FROM assignments asg WHERE asg.class_id = c.id) AS activities
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
    return jsonify(**{"class": class_json(row)}, students=class_students(class_id),
                   activities=class_assignments(class_id))


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
    # Also take them off activities given only to selected students of this class.
    database.execute(
        "DELETE FROM assignment_students WHERE student_id = ? "
        "AND assignment_id IN (SELECT id FROM assignments WHERE class_id = ?)",
        (student_id, class_id),
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
        "max_attempts": row["max_attempts"],  # None = unlimited
        # True once a student submitted it: then it can't be edited
        "locked": activity_has_submissions(row["id"]),
        # How many classes it is given to (0 = a draft)
        "assigned": db.get_db().execute(
            "SELECT COUNT(*) FROM assignments WHERE activity_id = ?", (row["id"],)
        ).fetchone()[0],
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
        # Answers students saved (not submitted yet) to a deleted question go with it.
        database.execute("DELETE FROM submission_answers WHERE question_id = ?", (question_id,))
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

    if activity_has_submissions(activity_id):
        return jsonify(error="A student already submitted this activity, so it can't be changed "
                             "anymore (their scores must stay fair)."), 400
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
    if database.execute("SELECT 1 FROM assignments WHERE activity_id = ?", (activity_id,)).fetchone():
        return jsonify(error="This activity was already given to a class, so it can't be deleted."), 400
    database.execute("DELETE FROM questions WHERE activity_id = ?", (activity_id,))
    database.execute("DELETE FROM activity_sections WHERE activity_id = ?", (activity_id,))
    database.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
    database.commit()
    return jsonify(ok=True)


# --- API: giving sheets to classes (teacher only) ------------------------------

# Due dates are calendar days at the school, wherever the server runs.
SCHOOL_TIMEZONE = ZoneInfo("Asia/Manila")


def school_today():
    return datetime.now(SCHOOL_TIMEZONE).date()


def assignment_students_of(assignment_id):
    return [row["student_id"] for row in db.get_db().execute(
        "SELECT student_id FROM assignment_students WHERE assignment_id = ?", (assignment_id,))]


def class_assignments(class_id):
    """The sheets given to a class, newest first: for the class page."""
    rows = db.get_db().execute(
        """
        SELECT asg.*, a.title, a.subject,
               (SELECT COUNT(*) FROM assignment_students s WHERE s.assignment_id = asg.id) AS selected
        FROM assignments asg JOIN activities a ON a.id = asg.activity_id
        WHERE asg.class_id = ?
        ORDER BY asg.assigned_at DESC, asg.id DESC
        """,
        (class_id,),
    ).fetchall()
    return [{
        "id": row["id"],
        "activity_id": row["activity_id"],
        "title": row["title"],
        "subject": row["subject"],
        "due_date": row["due_date"],
        "everyone": bool(row["everyone"]),
        "selected": row["selected"],
    } for row in rows]


@app.get("/api/activities/<int:activity_id>/assignments")
@role_required_api("teacher")
def api_get_assignments(activity_id):
    """All the teacher's classes with their students, and how this sheet is given to each
    (assignment is null when it isn't). Everything the Assign popup needs."""
    if find_my_activity(activity_id) is None:
        return jsonify(error="Activity not found."), 404
    database = db.get_db()
    classes = []
    for item in my_classes():
        row = database.execute(
            "SELECT * FROM assignments WHERE activity_id = ? AND class_id = ?", (activity_id, item["id"])
        ).fetchone()
        assignment = None
        if row:
            assignment = {
                "id": row["id"],
                "due_date": row["due_date"],
                "everyone": bool(row["everyone"]),
                "student_ids": assignment_students_of(row["id"]),
            }
        classes.append({
            "id": item["id"],
            "name": item["name"],
            "subject": item["subject"],
            "students": class_students(item["id"]),
            "assignment": assignment,
        })
    return jsonify(classes=classes, today=school_today().isoformat())


def assignment_fields(posted):
    """Clean one posted assignment: {class_id, everyone, student_ids, due_date}.
    Returns (dict, error message or None)."""
    if not isinstance(posted, dict):
        return None, "An assignment is not valid."
    class_row = find_my_class(posted.get("class_id"))
    if class_row is None:
        return None, "Class not found."
    name = class_row["name"] + (f" · {class_row['subject']}" if class_row["subject"] else "")

    due_date = posted.get("due_date") or None
    if due_date is not None:
        try:
            due_date = date.fromisoformat(str(due_date)).isoformat()
        except ValueError:
            return None, f"{name}: the due date is not valid."

    everyone = bool(posted.get("everyone", True))
    student_ids = []
    if not everyone:
        student_ids = posted.get("student_ids")
        if not isinstance(student_ids, list) or not student_ids:
            return None, f"{name}: choose at least one student, or give it to everyone."
        in_class = {student["id"] for student in class_students(class_row["id"])}
        if not set(student_ids) <= in_class:
            return None, f"{name}: a chosen student is not in this class."
        student_ids = sorted(set(student_ids))
    return {"class_id": class_row["id"], "everyone": everyone, "student_ids": student_ids,
            "due_date": due_date}, None


@app.put("/api/activities/<int:activity_id>/assignments")
@role_required_api("teacher")
def api_save_assignments(activity_id):
    """Give the sheet to the posted classes. The list is complete: classes left out stop
    having the sheet. Changing a class keeps its assignment id (students' work stays linked)."""
    if find_my_activity(activity_id) is None:
        return jsonify(error="Activity not found."), 404
    database = db.get_db()
    data = request.get_json(silent=True) or {}
    posted = data.get("assignments")
    if not isinstance(posted, list):
        return jsonify(error="Assignments must be a list."), 400
    if posted and not database.execute(
        "SELECT 1 FROM activity_sections WHERE activity_id = ?", (activity_id,)
    ).fetchone():
        return jsonify(error="Add at least one section before giving this activity to a class."), 400

    cleaned = []
    for item in posted:
        assignment, error = assignment_fields(item)
        if error:
            return jsonify(error=error), 400
        if any(other["class_id"] == assignment["class_id"] for other in cleaned):
            return jsonify(error="A class is listed twice."), 400
        cleaned.append(assignment)

    old = {row["class_id"]: row["id"] for row in database.execute(
        "SELECT id, class_id FROM assignments WHERE activity_id = ?", (activity_id,))}
    for assignment in cleaned:
        values = (1 if assignment["everyone"] else 0, assignment["due_date"])
        if assignment["class_id"] in old:
            assignment_id = old.pop(assignment["class_id"])
            database.execute("UPDATE assignments SET everyone = ?, due_date = ? WHERE id = ?",
                             (*values, assignment_id))
        else:
            assignment_id = database.execute(
                "INSERT INTO assignments (everyone, due_date, activity_id, class_id) VALUES (?, ?, ?, ?)",
                (*values, activity_id, assignment["class_id"]),
            ).lastrowid
        database.execute("DELETE FROM assignment_students WHERE assignment_id = ?", (assignment_id,))
        database.executemany(
            "INSERT INTO assignment_students (assignment_id, student_id) VALUES (?, ?)",
            [(assignment_id, student_id) for student_id in assignment["student_ids"]],
        )
    for class_id, assignment_id in old.items():  # classes no longer listed
        if database.execute(
            "SELECT 1 FROM submissions WHERE assignment_id = ? AND submitted_at IS NOT NULL", (assignment_id,)
        ).fetchone():
            database.rollback()
            name = class_json(find_my_class(class_id))["name"]
            return jsonify(error=f"Students in {name} already submitted, so it can't be taken back."), 400
        # Answers saved but not submitted yet are dropped with the assignment.
        database.execute(
            "DELETE FROM submission_answers WHERE submission_id IN "
            "(SELECT id FROM submissions WHERE assignment_id = ?)", (assignment_id,))
        database.execute("DELETE FROM submissions WHERE assignment_id = ?", (assignment_id,))
        database.execute("DELETE FROM assignment_students WHERE assignment_id = ?", (assignment_id,))
        database.execute("DELETE FROM assignments WHERE id = ?", (assignment_id,))
    database.commit()
    return api_get_assignments(activity_id)


def activity_has_submissions(activity_id):
    """True once any student submitted this sheet (in any class)."""
    return db.get_db().execute(
        "SELECT 1 FROM submissions sub JOIN assignments asg ON asg.id = sub.assignment_id "
        "WHERE asg.activity_id = ? AND sub.submitted_at IS NOT NULL LIMIT 1",
        (activity_id,),
    ).fetchone() is not None


# --- Students answering ----------------------------------------------------------

MAX_SHORT_ANSWER_LENGTH = 5000

# A student sees an assignment when they are in its class and it is for everyone,
# or they are one of its chosen students.
VISIBLE_TO_STUDENT = """
    asg.class_id IN (SELECT class_id FROM class_students WHERE student_id = :student)
    AND (asg.everyone = 1 OR EXISTS (SELECT 1 FROM assignment_students s
                                     WHERE s.assignment_id = asg.id AND s.student_id = :student))
"""


def student_assignments(student_id):
    """Everything given to a student, with how far they are: for My activities."""
    rows = db.get_db().execute(
        f"""
        SELECT asg.id, asg.due_date, a.title, a.subject, a.id AS activity_id, a.max_attempts,
               c.name AS class_name, c.subject AS class_subject, t.name AS teacher,
               sub.id AS submission_id, sub.submitted_at, sub.attempt, sub.paper,
               last.id AS last_id, last.late AS last_late, last.paper AS last_paper
        FROM assignments asg
        JOIN activities a ON a.id = asg.activity_id
        JOIN classes c ON c.id = asg.class_id
        JOIN users t ON t.id = a.teacher_id
        -- sub: the student's latest attempt; last: their latest submitted attempt (the one that counts)
        LEFT JOIN submissions sub ON sub.id = (
            SELECT id FROM submissions WHERE assignment_id = asg.id AND student_id = :student
            ORDER BY attempt DESC LIMIT 1)
        LEFT JOIN submissions last ON last.id = (
            SELECT id FROM submissions WHERE assignment_id = asg.id AND student_id = :student
            AND submitted_at IS NOT NULL ORDER BY attempt DESC LIMIT 1)
        WHERE {VISIBLE_TO_STUDENT}
        ORDER BY asg.due_date IS NULL, asg.due_date, asg.assigned_at DESC
        """,
        {"student": student_id},
    ).fetchall()
    today = school_today().isoformat()
    result = []
    for row in rows:
        if row["submitted_at"]:
            status = "submitted"
        elif row["submission_id"]:
            status = "in_progress"
        else:
            status = "not_started"
        item = {
            "id": row["id"],
            "title": row["title"],
            "subject": row["subject"],
            "class_name": row["class_name"] + (f" · {row['class_subject']}" if row["class_subject"] else ""),
            "teacher": row["teacher"],
            "due_date": row["due_date"],
            # Overdue only when nothing was ever submitted
            "overdue": bool(row["due_date"] and row["last_id"] is None and today > row["due_date"]),
            "status": status,
            "attempt": row["attempt"] or 0,
            "max_attempts": row["max_attempts"],
            "can_retry": status == "submitted" and can_try_again(row, row["max_attempts"]),
            "late": bool(row["last_late"]),
            "paper": bool(row["last_paper"]),
            # The score that counts: the latest submitted attempt
            "score": score_summary(row["last_id"], row["activity_id"])["total"] if row["last_id"] else None,
        }
        result.append(item)
    return result


def find_student_assignment(assignment_id):
    """The assignment with its activity, if the logged-in student was given it."""
    return db.get_db().execute(
        f"""
        SELECT asg.*, a.title, a.subject, a.teacher_id, a.max_attempts,
               c.name AS class_name, c.subject AS class_subject, t.name AS teacher
        FROM assignments asg
        JOIN activities a ON a.id = asg.activity_id
        JOIN classes c ON c.id = asg.class_id
        JOIN users t ON t.id = a.teacher_id
        WHERE asg.id = :assignment AND {VISIBLE_TO_STUDENT}
        """,
        {"assignment": assignment_id, "student": current_user()["id"]},
    ).fetchone()


def find_submission(assignment_id, student_id, submitted_only=False):
    """The student's latest attempt (or latest submitted one), or None."""
    return db.get_db().execute(
        "SELECT * FROM submissions WHERE assignment_id = ? AND student_id = ?"
        + (" AND submitted_at IS NOT NULL" if submitted_only else "")
        + " ORDER BY attempt DESC LIMIT 1",
        (assignment_id, student_id),
    ).fetchone()


def can_try_again(submission, max_attempts):
    """After submitting this attempt: may the student start another one by themselves?
    Not after a paper score: only the teacher can reopen it (Give another try)."""
    if submission["paper"]:
        return False
    return max_attempts is None or submission["attempt"] < max_attempts


def question_for_student(question):
    """A question without its answer key (students must never receive it)."""
    result = {key: question[key] for key in ("id", "type", "prompt", "choices", "points")}
    if question["type"] == "fill_blank":
        result["blanks"] = len(question["answer"])
    return result


def normalize(text):
    """For checking typed answers: capital letters and extra spaces don't matter."""
    return " ".join(str(text).split()).casefold()


def clean_student_answer(question, value):
    """Check one answer from a student. Returns (value to save or None when unanswered, error or None)."""
    kind = question["type"]
    if value is None:
        return None, None
    if kind == "multiple_choice":
        if isinstance(value, int) and not isinstance(value, bool) and 0 <= value < len(question["choices"]):
            return value, None
    elif kind == "true_false":
        if isinstance(value, bool):
            return value, None
    elif kind in ("identification", "short_answer"):
        if isinstance(value, str):
            limit = MAX_SHORT_ANSWER_LENGTH if kind == "short_answer" else MAX_ANSWER_LENGTH
            value = clean_description(value) if kind == "short_answer" else " ".join(value.split())
            if len(value) > limit:
                return None, f"An answer is too long (at most {limit} characters)."
            return (value or None), None
    elif kind == "fill_blank":
        blanks = len(question["answer"])
        if isinstance(value, list) and len(value) == blanks and all(isinstance(item, str) for item in value):
            value = [" ".join(item.split()) for item in value]
            if any(len(item) > MAX_ANSWER_LENGTH for item in value):
                return None, f"An answer is too long (at most {MAX_ANSWER_LENGTH} characters)."
            return (value if any(value) else None), None
    return None, "An answer is not valid."


def check_answer(question, value):
    """(is_correct, points) for a submitted answer. Short answers: (None, None) — the teacher scores them.
    Fill in the blank gives part of the points for each right blank."""
    kind = question["type"]
    if kind == "short_answer":
        return None, None
    if value is None:
        return False, 0
    if kind in ("multiple_choice", "true_false"):
        correct = value == question["answer"]
        return correct, question["points"] if correct else 0
    if kind == "identification":
        correct = normalize(value) in {normalize(answer) for answer in question["answer"]}
        return correct, question["points"] if correct else 0
    right = sum(
        normalize(given) in {normalize(answer) for answer in accepted}
        for given, accepted in zip(value, question["answer"])
    )
    blanks = len(question["answer"])
    return right == blanks, question["points"] * right // blanks


def saved_answers(submission_id):
    """{question id: answer} of a submission."""
    if submission_id is None:
        return {}
    return {row["question_id"]: json.loads(row["answer"]) for row in db.get_db().execute(
        "SELECT question_id, answer FROM submission_answers WHERE submission_id = ?", (submission_id,))}


def score_summary(submission_id, activity_id):
    """Points per activity section and in total: earned, possible, and pending (short answers
    the teacher hasn't scored yet). A paper score has a total only (paper: True)."""
    database = db.get_db()
    submission = database.execute("SELECT paper, paper_score FROM submissions WHERE id = ?",
                                  (submission_id,)).fetchone()
    if submission and submission["paper"]:
        possible = database.execute("SELECT COALESCE(SUM(points), 0) FROM questions WHERE activity_id = ?",
                                    (activity_id,)).fetchone()[0]
        return {"total": {"earned": submission["paper_score"], "possible": possible, "pending": 0},
                "sections": {}, "paper": True}
    rows = database.execute(
        """
        SELECT q.section_id, q.points AS possible, sa.points AS earned, q.type
        FROM questions q
        LEFT JOIN submission_answers sa ON sa.question_id = q.id AND sa.submission_id = ?
        WHERE q.activity_id = ?
        """,
        (submission_id, activity_id),
    ).fetchall()
    sections = {}
    total = {"earned": 0, "possible": 0, "pending": 0}
    for row in rows:
        part = sections.setdefault(row["section_id"], {"earned": 0, "possible": 0, "pending": 0})
        pending = row["type"] == "short_answer" and row["earned"] is None
        for bucket in (part, total):
            bucket["possible"] += row["possible"]
            if pending:
                bucket["pending"] += row["possible"]
            else:
                bucket["earned"] += row["earned"] or 0
    return {"total": total, "sections": sections, "paper": False}


def save_student_answers(submission_id, questions, posted):
    """Save the posted {question id: answer} (only questions of this sheet). The caller commits.
    Returns an error message or None."""
    if not isinstance(posted, dict):
        return "Answers are not valid."
    by_id = {str(question["id"]): question for question in questions}
    database = db.get_db()
    for key, value in posted.items():
        question = by_id.get(str(key))
        if question is None:
            continue  # a question removed by the teacher while the student worked
        value, error = clean_student_answer(question, value)
        if error:
            return error
        if value is None:
            database.execute("DELETE FROM submission_answers WHERE submission_id = ? AND question_id = ?",
                             (submission_id, question["id"]))
        else:
            database.execute(
                "INSERT INTO submission_answers (submission_id, question_id, answer) VALUES (?, ?, ?) "
                "ON CONFLICT (submission_id, question_id) DO UPDATE SET answer = excluded.answer",
                (submission_id, question["id"], json.dumps(value)),
            )
    database.execute("UPDATE submissions SET updated_at = datetime('now') WHERE id = ?", (submission_id,))
    return None


def start_submission(assignment_id):
    """The student's current attempt, made (as attempt 1) the first time they save."""
    student_id = current_user()["id"]
    submission = find_submission(assignment_id, student_id)
    if submission is None:
        db.get_db().execute(
            "INSERT INTO submissions (assignment_id, student_id, attempt) VALUES (?, ?, 1)",
            (assignment_id, student_id),
        )
        submission = find_submission(assignment_id, student_id)
    return submission


def sheet_questions(activity_id):
    return [question for section in activity_sections(activity_id) for question in section["questions"]]


@app.get("/api/my-activities")
@role_required_api("student")
def api_my_activities():
    return jsonify(activities=student_assignments(current_user()["id"]), today=school_today().isoformat())


@app.get("/api/my-activities/<int:assignment_id>")
@role_required_api("student")
def api_my_activity(assignment_id):
    """The sheet to answer (no answer keys), the student's saved answers, and after submitting
    their score."""
    assignment = find_student_assignment(assignment_id)
    if assignment is None:
        return jsonify(error="Activity not found."), 404
    submission = find_submission(assignment_id, current_user()["id"])
    last_submitted = find_submission(assignment_id, current_user()["id"], submitted_only=True)
    sections = activity_sections(assignment["activity_id"])
    for section in sections:
        section["questions"] = [question_for_student(question) for question in section["questions"]]

    result = {
        "id": assignment_id,
        "title": assignment["title"],
        "subject": assignment["subject"],
        "class_name": assignment["class_name"]
        + (f" · {assignment['class_subject']}" if assignment["class_subject"] else ""),
        "teacher": assignment["teacher"],
        "due_date": assignment["due_date"],
        "sections": sections,
        "answers": saved_answers(submission["id"] if submission else None),
        "submitted_at": submission["submitted_at"] if submission else None,
        "attempt": submission["attempt"] if submission else 1,
        "max_attempts": assignment["max_attempts"],
        "can_retry": bool(submission and submission["submitted_at"]
                          and can_try_again(submission, assignment["max_attempts"])),
        # The latest submitted attempt counts. While working on a new attempt, this is the
        # earlier one's score (submitting again replaces it).
        "score": score_summary(last_submitted["id"], assignment["activity_id"]) if last_submitted else None,
        "late": bool(last_submitted and last_submitted["late"]),
        "paper": bool(last_submitted and last_submitted["paper"]),
        "note": last_submitted["note"] if last_submitted else "",
    }
    return jsonify(activity=result)


@app.put("/api/my-activities/<int:assignment_id>/answers")
@role_required_api("student")
def api_save_my_answers(assignment_id):
    """Save answers while working (called automatically as the student types)."""
    assignment = find_student_assignment(assignment_id)
    if assignment is None:
        return jsonify(error="Activity not found."), 404
    submission = find_submission(assignment_id, current_user()["id"])
    if submission and submission["submitted_at"]:
        return jsonify(error="You already submitted this activity."), 400
    submission = start_submission(assignment_id)
    error = save_student_answers(submission["id"], sheet_questions(assignment["activity_id"]),
                                 (request.get_json(silent=True) or {}).get("answers", {}))
    if error:
        db.get_db().rollback()
        return jsonify(error=error), 400
    db.get_db().commit()
    return jsonify(ok=True)


@app.post("/api/my-activities/<int:assignment_id>/submit")
@role_required_api("student")
def api_submit_my_activity(assignment_id):
    """Save the last answers, check them, and submit (only once). Late when after the due date."""
    assignment = find_student_assignment(assignment_id)
    if assignment is None:
        return jsonify(error="Activity not found."), 404
    submission = find_submission(assignment_id, current_user()["id"])
    if submission and submission["submitted_at"]:
        return jsonify(error="You already submitted this activity."), 400

    database = db.get_db()
    submission = start_submission(assignment_id)
    questions = sheet_questions(assignment["activity_id"])
    error = save_student_answers(submission["id"], questions,
                                 (request.get_json(silent=True) or {}).get("answers", {}))
    if error:
        database.rollback()
        return jsonify(error=error), 400

    answers = saved_answers(submission["id"])
    # Short answers the teacher already scored in the previous attempt keep their score when
    # the student didn't change them, so the teacher doesn't check the same text twice.
    previous = find_submission(assignment_id, current_user()["id"], submitted_only=True)
    previous_scores = {} if previous is None else {
        row["question_id"]: (row["answer"], row["points"]) for row in database.execute(
            "SELECT question_id, answer, points FROM submission_answers WHERE submission_id = ? "
            "AND points IS NOT NULL", (previous["id"],))}
    for question in questions:
        is_correct, points = check_answer(question, answers.get(question["id"]))
        earlier = previous_scores.get(question["id"])
        if question["type"] == "short_answer" and earlier and question["id"] in answers \
                and json.loads(earlier[0]) == answers[question["id"]]:
            points = earlier[1]
            is_correct = points == question["points"]
        if question["id"] not in answers:
            # Unanswered: saved as an empty answer so it shows as 0 points (short answers too).
            database.execute(
                "INSERT INTO submission_answers (submission_id, question_id, answer, is_correct, points) "
                "VALUES (?, ?, 'null', 0, 0)",
                (submission["id"], question["id"]),
            )
            continue
        database.execute(
            "UPDATE submission_answers SET is_correct = ?, points = ? WHERE submission_id = ? AND question_id = ?",
            (None if is_correct is None else int(is_correct), points, submission["id"], question["id"]),
        )
    late = bool(assignment["due_date"] and school_today().isoformat() > assignment["due_date"])
    database.execute(
        "UPDATE submissions SET submitted_at = datetime('now'), updated_at = datetime('now'), late = ? WHERE id = ?",
        (int(late), submission["id"]),
    )
    database.commit()
    return api_my_activity(assignment_id)


@app.post("/api/my-activities/<int:assignment_id>/retry")
@role_required_api("student")
def api_retry_my_activity(assignment_id):
    """Start the next attempt, if the activity allows more. It starts with the answers of the
    last attempt so the student only changes what they want."""
    assignment = find_student_assignment(assignment_id)
    if assignment is None:
        return jsonify(error="Activity not found."), 404
    submission = find_submission(assignment_id, current_user()["id"])
    if submission is None or not submission["submitted_at"]:
        return jsonify(error="Submit this activity first."), 400
    if submission["paper"]:
        return jsonify(error="Your teacher already scored this from your paper."), 400
    if not can_try_again(submission, assignment["max_attempts"]):
        return jsonify(error="You have used all your tries for this activity."), 400

    database = db.get_db()
    new_id = database.execute(
        "INSERT INTO submissions (assignment_id, student_id, attempt) VALUES (?, ?, ?)",
        (assignment_id, current_user()["id"], submission["attempt"] + 1),
    ).lastrowid
    database.execute(
        "INSERT INTO submission_answers (submission_id, question_id, answer) "
        "SELECT ?, question_id, answer FROM submission_answers WHERE submission_id = ? AND answer != 'null'",
        (new_id, submission["id"]),
    )
    database.commit()
    return api_my_activity(assignment_id)


MAX_ATTEMPTS_CHOICE = 10


@app.put("/api/activities/<int:activity_id>/settings")
@role_required_api("teacher")
def api_activity_settings(activity_id):
    """Settings that may change anytime, even after students submitted:
    max_attempts (1 to 10, or null = unlimited)."""
    if find_my_activity(activity_id) is None:
        return jsonify(error="Activity not found."), 404
    data = request.get_json(silent=True) or {}
    max_attempts = data.get("max_attempts")
    if max_attempts is not None and (
        not isinstance(max_attempts, int) or isinstance(max_attempts, bool)
        or not 1 <= max_attempts <= MAX_ATTEMPTS_CHOICE
    ):
        return jsonify(error=f"Submissions allowed must be 1 to {MAX_ATTEMPTS_CHOICE}, or unlimited."), 400
    database = db.get_db()
    database.execute("UPDATE activities SET max_attempts = ? WHERE id = ?", (max_attempts, activity_id))
    database.commit()
    return jsonify(activity=activity_json(find_my_activity(activity_id)))


# --- Results (teacher) -----------------------------------------------------------

def find_my_assignment(assignment_id):
    """An assignment of the logged-in teacher's sheet, with the sheet and class details."""
    return db.get_db().execute(
        """
        SELECT asg.*, a.title, a.subject, a.max_attempts, c.name AS class_name, c.subject AS class_subject
        FROM assignments asg
        JOIN activities a ON a.id = asg.activity_id
        JOIN classes c ON c.id = asg.class_id
        WHERE asg.id = ? AND a.teacher_id = ?
        """,
        (assignment_id, current_user()["id"]),
    ).fetchone()


def assigned_students(assignment):
    """The students who got this assignment, plus anyone who already worked on it
    (e.g. removed from the class later), in name order."""
    if assignment["everyone"]:
        given = "SELECT student_id FROM class_students WHERE class_id = :class"
    else:
        given = ("SELECT student_id FROM assignment_students WHERE assignment_id = :assignment "
                 "AND student_id IN (SELECT student_id FROM class_students WHERE class_id = :class)")
    return db.get_db().execute(
        f"""
        SELECT * FROM users WHERE role = 'student' AND (
            id IN ({given}) OR id IN (SELECT student_id FROM submissions WHERE assignment_id = :assignment))
        ORDER BY name COLLATE NOCASE
        """,
        {"class": assignment["class_id"], "assignment": assignment["id"]},
    ).fetchall()


def student_attempts(assignment_id, student_id):
    return db.get_db().execute(
        "SELECT * FROM submissions WHERE assignment_id = ? AND student_id = ? ORDER BY attempt",
        (assignment_id, student_id),
    ).fetchall()


def class_title(name, subject):
    return name + (f" · {subject}" if subject else "")


@app.get("/api/assignments/<int:assignment_id>/results")
@role_required_api("teacher")
def api_results(assignment_id):
    assignment = find_my_assignment(assignment_id)
    if assignment is None:
        return jsonify(error="Not found."), 404
    return jsonify(results_data(assignment))


def results_data(assignment):
    """Every student of the assignment with status, attempts and the score that counts
    (latest submitted attempt), in total and per activity section, plus a summary.
    Used by the results page and the Excel/PDF exports."""
    assignment_id = assignment["id"]
    activity_id = assignment["activity_id"]
    sections = [{"id": section["id"], "title": section["title"] or f"Section {number}",
                 "points": sum(question["points"] for question in section["questions"])}
                for number, section in enumerate(activity_sections(activity_id), start=1)
                if section["kind"] == "activity"]

    students = []
    for student in assigned_students(assignment):
        attempts = student_attempts(assignment_id, student["id"])
        submitted = [attempt for attempt in attempts if attempt["submitted_at"]]
        latest = attempts[-1] if attempts else None
        counted = submitted[-1] if submitted else None
        if latest is None:
            status = "not_started"
        elif latest["submitted_at"]:
            status = "submitted"
        else:
            status = "in_progress"  # first time, or trying again
        score = score_summary(counted["id"], activity_id) if counted else None
        students.append({
            **user_json(student),
            "status": status,
            "attempts": len(submitted),
            "submitted_at": counted["submitted_at"] if counted else None,
            "late": bool(counted and counted["late"]),
            "paper": bool(counted and counted["paper"]),
            "score": score["total"] if score else None,
            "section_scores": {str(key): value for key, value in score["sections"].items()} if score else {},
        })

    scored = [student["score"] for student in students if student["score"]]
    summary = {
        "students": len(students),
        "submitted": len(scored),
        "not_started": sum(student["status"] == "not_started" for student in students),
        "late": sum(student["late"] for student in students),
        "to_check": sum(score["pending"] for score in scored),
        # Average of what's checked so far, as a percent
        "average": round(100 * sum(score["earned"] for score in scored)
                         / sum(score["possible"] - score["pending"] for score in scored))
        if scored and sum(score["possible"] - score["pending"] for score in scored) else None,
    }
    return {
        "assignment": {
            "id": assignment_id,
            "activity_id": activity_id,
            "title": assignment["title"],
            "subject": assignment["subject"],
            "class_id": assignment["class_id"],
            "class_name": class_title(assignment["class_name"], assignment["class_subject"]),
            "due_date": assignment["due_date"],
            "everyone": bool(assignment["everyone"]),
            "max_attempts": assignment["max_attempts"],
            "total_points": total_points(activity_id),
        },
        "sections": sections,
        "students": students,
        "summary": summary,
    }


def submission_detail(submission, activity_id):
    """One attempt for the teacher: every section and question with the answer key, the
    student's answer, whether it is right, and the points."""
    database = db.get_db()
    rows = {row["question_id"]: row for row in database.execute(
        "SELECT * FROM submission_answers WHERE submission_id = ?", (submission["id"],))}
    sections = activity_sections(activity_id)
    for section in sections:
        for question in section["questions"]:
            row = rows.get(question["id"])
            question["given"] = json.loads(row["answer"]) if row else None
            question["is_correct"] = None if row is None or row["is_correct"] is None else bool(row["is_correct"])
            question["earned"] = row["points"] if row else None
    return {
        "id": submission["id"],
        "attempt": submission["attempt"],
        "submitted_at": submission["submitted_at"],
        "late": bool(submission["late"]),
        "paper": bool(submission["paper"]),
        "note": submission["note"],
        "score": score_summary(submission["id"], activity_id) if submission["submitted_at"] else None,
        "sections": sections,
    }


@app.get("/api/assignments/<int:assignment_id>/students/<int:student_id>")
@role_required_api("teacher")
def api_student_result(assignment_id, student_id):
    """One student's work: their attempts, and one attempt in detail (?attempt=, default the
    latest submitted one, or the latest if none was submitted)."""
    assignment = find_my_assignment(assignment_id)
    if assignment is None:
        return jsonify(error="Not found."), 404
    student = db.get_db().execute("SELECT * FROM users WHERE id = ? AND role = 'student'", (student_id,)).fetchone()
    if student is None:
        return jsonify(error="Student not found."), 404
    attempts = student_attempts(assignment_id, student_id)
    detail = None
    if attempts:
        wanted = request.args.get("attempt", type=int)
        submitted = [attempt for attempt in attempts if attempt["submitted_at"]]
        chosen = next((attempt for attempt in attempts if attempt["attempt"] == wanted), None) \
            or (submitted[-1] if submitted else attempts[-1])
        detail = submission_detail(chosen, assignment["activity_id"])
    counted = next((attempt for attempt in reversed(attempts) if attempt["submitted_at"]), None)
    return jsonify(
        student=user_json(student),
        attempts=[{
            "attempt": attempt["attempt"],
            "submitted_at": attempt["submitted_at"],
            "late": bool(attempt["late"]),
            "paper": bool(attempt["paper"]),
            "counts": counted is not None and attempt["id"] == counted["id"],
        } for attempt in attempts],
        detail=detail,
        can_reopen=bool(attempts and attempts[-1]["submitted_at"]),
        possible=db.get_db().execute("SELECT COALESCE(SUM(points), 0) FROM questions WHERE activity_id = ?",
                                     (assignment["activity_id"],)).fetchone()[0],
    )


def find_my_submission(submission_id):
    """A submission of the logged-in teacher's sheet, with its activity id."""
    return db.get_db().execute(
        """
        SELECT sub.*, asg.activity_id FROM submissions sub
        JOIN assignments asg ON asg.id = sub.assignment_id
        JOIN activities a ON a.id = asg.activity_id
        WHERE sub.id = ? AND a.teacher_id = ?
        """,
        (submission_id, current_user()["id"]),
    ).fetchone()


@app.put("/api/submissions/<int:submission_id>/points")
@role_required_api("teacher")
def api_set_points(submission_id):
    """The teacher scores a submitted attempt: {points: {question id: points}}. Used for short
    answers, and to change any auto-checked score (e.g. accept a different spelling)."""
    submission = find_my_submission(submission_id)
    if submission is None:
        return jsonify(error="Not found."), 404
    if not submission["submitted_at"]:
        return jsonify(error="The student hasn't submitted this attempt yet."), 400
    if submission["paper"]:
        return jsonify(error="This is a paper score: change its total instead."), 400
    posted = (request.get_json(silent=True) or {}).get("points")
    if not isinstance(posted, dict):
        return jsonify(error="Points are not valid."), 400

    database = db.get_db()
    questions = {str(question["id"]): question for question in sheet_questions(submission["activity_id"])}
    for key, points in posted.items():
        question = questions.get(str(key))
        if question is None:
            return jsonify(error="Question not found."), 400
        if points is None and question["type"] == "short_answer":
            value = None  # back to "to check"
        elif isinstance(points, int) and not isinstance(points, bool) and 0 <= points <= question["points"]:
            value = points
        else:
            return jsonify(error=f"Points must be a whole number from 0 to {question['points']}."), 400
        database.execute(
            "INSERT INTO submission_answers (submission_id, question_id, answer, is_correct, points) "
            "VALUES (?, ?, 'null', ?, ?) "
            "ON CONFLICT (submission_id, question_id) DO UPDATE SET is_correct = excluded.is_correct, "
            "points = excluded.points",
            (submission_id, question["id"],
             None if value is None else int(value == question["points"]), value),
        )
    database.commit()
    return jsonify(detail=submission_detail(find_my_submission(submission_id), submission["activity_id"]))


@app.post("/api/assignments/<int:assignment_id>/students/<int:student_id>/reopen")
@role_required_api("teacher")
def api_reopen(assignment_id, student_id):
    """Give one student another try, even past the activity's limit: a new attempt starting
    from their last answers. Their counted score stays until they submit it."""
    assignment = find_my_assignment(assignment_id)
    if assignment is None:
        return jsonify(error="Not found."), 404
    attempts = student_attempts(assignment_id, student_id)
    if not attempts:
        return jsonify(error="The student hasn't started yet."), 400
    if not attempts[-1]["submitted_at"]:
        return jsonify(error="The student is already answering (not submitted yet)."), 400
    last = attempts[-1]
    database = db.get_db()
    new_id = database.execute(
        "INSERT INTO submissions (assignment_id, student_id, attempt) VALUES (?, ?, ?)",
        (assignment_id, student_id, last["attempt"] + 1),
    ).lastrowid
    database.execute(
        "INSERT INTO submission_answers (submission_id, question_id, answer) "
        "SELECT ?, question_id, answer FROM submission_answers WHERE submission_id = ? AND answer != 'null'",
        (new_id, last["id"]),
    )
    database.commit()
    return api_student_result(assignment_id, student_id)


# --- Paper scores (teacher) ------------------------------------------------------

MAX_NOTE_LENGTH = 200


def paper_fields(data, possible):
    """Clean {score, late, note} for a paper score. Returns (score, late, note, error or None)."""
    score = data.get("score")
    if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= possible:
        return None, None, None, f"The score must be a whole number from 0 to {possible}."
    note = clean_name(data.get("note"))
    if len(note) > MAX_NOTE_LENGTH:
        return None, None, None, f"The note can be at most {MAX_NOTE_LENGTH} characters."
    return score, bool(data.get("late")), note, None


def total_points(activity_id):
    return db.get_db().execute(
        "SELECT COALESCE(SUM(points), 0) FROM questions WHERE activity_id = ?", (activity_id,)
    ).fetchone()[0]


@app.post("/api/assignments/<int:assignment_id>/students/<int:student_id>/paper")
@role_required_api("teacher")
def api_add_paper_score(assignment_id, student_id):
    """The student answered on paper: save the total score the teacher gives as a new attempt
    (the latest submission counts). {score, late, note}"""
    assignment = find_my_assignment(assignment_id)
    if assignment is None:
        return jsonify(error="Not found."), 404
    if student_id not in {row["id"] for row in assigned_students(assignment)}:
        return jsonify(error="This student doesn't have this activity."), 404
    possible = total_points(assignment["activity_id"])
    if possible == 0:
        return jsonify(error="This activity has no questions to score."), 400
    score, late, note, error = paper_fields(request.get_json(silent=True) or {}, possible)
    if error:
        return jsonify(error=error), 400

    database = db.get_db()
    attempts = student_attempts(assignment_id, student_id)
    database.execute(
        "INSERT INTO submissions (assignment_id, student_id, attempt, submitted_at, late, paper, paper_score, note) "
        "VALUES (?, ?, ?, datetime('now'), ?, 1, ?, ?)",
        (assignment_id, student_id, (attempts[-1]["attempt"] + 1) if attempts else 1, int(late), score, note),
    )
    database.commit()
    return api_student_result(assignment_id, student_id)


@app.put("/api/submissions/<int:submission_id>/paper")
@role_required_api("teacher")
def api_edit_paper_score(submission_id):
    """Change a paper score: {score, late, note}."""
    submission = find_my_submission(submission_id)
    if submission is None or not submission["paper"]:
        return jsonify(error="Paper score not found."), 404
    score, late, note, error = paper_fields(request.get_json(silent=True) or {},
                                            total_points(submission["activity_id"]))
    if error:
        return jsonify(error=error), 400
    database = db.get_db()
    database.execute("UPDATE submissions SET paper_score = ?, late = ?, note = ? WHERE id = ?",
                     (score, int(late), note, submission_id))
    database.commit()
    return api_student_result(submission["assignment_id"], submission["student_id"])


@app.delete("/api/submissions/<int:submission_id>/paper")
@role_required_api("teacher")
def api_delete_paper_score(submission_id):
    """Remove a paper score (e.g. typed for the wrong student). The attempt before it counts again."""
    submission = find_my_submission(submission_id)
    if submission is None or not submission["paper"]:
        return jsonify(error="Paper score not found."), 404
    database = db.get_db()
    database.execute("DELETE FROM submissions WHERE id = ?", (submission_id,))
    database.commit()
    return api_student_result(submission["assignment_id"], submission["student_id"])

