"""Admin: supervisor accounts (a read-only role that only sees the activity log)."""

from conftest import flask_app

PASSWORD = "123qwe"  # long enough for a new account (the sample accounts use a shorter one)


def make_supervisor(admin, username="gsupervisor"):
    response = admin.post("/api/users", json={"role": "supervisor", "last_name": "Garcia", "first_name": "Sam",
                                              "username": username, "password": PASSWORD})
    assert response.status_code == 201, response.get_json()
    return response.get_json()["user"]


def test_admin_creates_and_lists_supervisor(admin, teacher):
    teachers_before = admin.get("/api/users?role=teacher").get_json()["total"]
    user = make_supervisor(admin)
    assert user["role"] == "supervisor" and user["grade"] == "" and user["section"] == ""
    listed = admin.get("/api/users?role=supervisor").get_json()
    assert [account["username"] for account in listed["users"]] == ["gsupervisor"]
    assert admin.get("/api/users?role=teacher").get_json()["total"] == teachers_before  # supervisors are not in the other lists
    assert teacher.post("/api/users", json={"role": "supervisor", "last_name": "X", "first_name": "Y",
                                            "username": "xy"}).status_code == 403


def test_supervisor_must_change_password_first_login(admin):
    make_supervisor(admin)
    response = _login_response("gsupervisor")
    assert response.status_code == 200 and response.get_json()["must_change_password"] is True


def test_admin_can_edit_and_deactivate_a_supervisor(admin):
    user = make_supervisor(admin)
    response = admin.put(f"/api/users/{user['id']}", json={"first_name": "Samuel", "active": False})
    assert response.status_code == 200 and response.get_json()["user"]["active"] is False


def test_supervisors_page_and_dashboard_count(admin, teacher):
    make_supervisor(admin)
    assert admin.get("/supervisors").status_code == 200
    assert teacher.get("/supervisors").status_code == 302
    assert admin.get("/api/dashboard").get_json()["supervisors"] == 1


def test_migration_adds_supervisor_and_keeps_users(app):
    from myguro.database import get_db, init_db

    with app.app_context():
        db = get_db()
        before = [tuple(row) for row in db.execute(
            "SELECT id, username, password_hash, role FROM users ORDER BY id")]
        # Turn users back into the old table, whose CHECK does not know supervisor
        old_sql = db.execute("SELECT sql FROM sqlite_master WHERE name = 'users'").fetchone()[0]
        old_sql = old_sql.replace("'admin', 'teacher', 'student', 'supervisor'", "'admin', 'teacher', 'student'")
        db.commit()
        db.execute("PRAGMA foreign_keys = OFF")
        db.execute("PRAGMA legacy_alter_table = ON")
        db.execute("ALTER TABLE users RENAME TO users_tmp")
        db.execute("PRAGMA legacy_alter_table = OFF")
        db.execute(old_sql)
        db.execute("INSERT INTO users SELECT * FROM users_tmp")
        db.execute("DROP TABLE users_tmp")
        db.commit()
        db.execute("PRAGMA foreign_keys = ON")
        assert "supervisor" not in db.execute("SELECT sql FROM sqlite_master WHERE name = 'users'").fetchone()[0]

        init_db()
        init_db()  # a second run changes nothing
        after = [tuple(row) for row in db.execute("SELECT id, username, password_hash, role FROM users ORDER BY id")]
        assert after == before
        db.execute("INSERT INTO users (name, username, password_hash, role) VALUES ('S', 'sup', 'x', 'supervisor')")
        db.commit()


def _login_response(username, password=PASSWORD):
    return flask_app.test_client().post("/api/login", json={"username": username, "password": password})


def test_one_users_tab_with_a_role_filter(admin):
    dashboard = admin.get("/dashboard").get_data(as_text=True)
    assert 'href="/users"' in dashboard
    tabs = dashboard.split('class="nav nav-underline"')[1].split("</ul>")[0]  # the top tabs
    assert "Users" in tabs and "Log" in tabs
    assert "Teachers" not in tabs and "Students" not in tabs and "Supervisors" not in tabs
    for role, noun in (("teacher", "Teachers"), ("student", "Students"), ("supervisor", "Supervisors")):
        page = admin.get(f"/users?role={role}").get_data(as_text=True)
        assert f'data-role="{role}"' in page and f"<title>{noun} · MyGuro</title>" in page
        assert f'<option value="{role}" selected>' in page
    assert 'data-role="student"' in admin.get("/users").get_data(as_text=True)  # the default
    assert 'data-role="student"' in admin.get("/users?role=boss").get_data(as_text=True)
