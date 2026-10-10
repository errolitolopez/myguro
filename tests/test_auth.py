"""Login, logout, password change, and who may open what."""

from conftest import error, login


def test_login_wrong_password(app):
    client = app.test_client()
    response = client.post("/api/login", json={"username": "ecruz", "password": "nope"})
    assert response.status_code == 401
    assert error(response) == "Wrong username or password."


def test_login_needs_username_and_password(app):
    assert app.test_client().post("/api/login", json={}).status_code == 400


def test_username_is_not_case_sensitive(app):
    response = app.test_client().post("/api/login", json={"username": "ECRUZ", "password": "1234"})
    assert response.status_code == 200


def test_lockout_after_five_wrong_tries(app):
    client = app.test_client()
    for _ in range(5):
        client.post("/api/login", json={"username": "lmanalo", "password": "bad"})
    response = client.post("/api/login", json={"username": "lmanalo", "password": "1234"})
    assert response.status_code == 429


def test_default_admin_must_change_password(app):
    client = login("admin", "admin")
    assert client.get("/dashboard").headers["Location"].endswith("/change-password")
    response = client.get("/api/dashboard")
    assert response.status_code == 403 and response.get_json()["must_change_password"] is True
    assert error(client.post("/api/change-password",
                             json={"current_password": "admin", "new_password": "short"})).startswith(
        "New password must be at least 8")
    assert client.post("/api/change-password",
                       json={"current_password": "admin", "new_password": "adminpass1"}).status_code == 200
    assert client.get("/dashboard").status_code == 200


def test_change_password_rules(teacher):
    assert error(teacher.post("/api/change-password",
                              json={"current_password": "wrong", "new_password": "abcdefgh1"})) == \
        "Current password is wrong."
    assert error(teacher.post("/api/change-password",
                              json={"current_password": "1234", "new_password": "ecruz"})).startswith("New password")
    assert error(teacher.post("/api/change-password",
                              json={"current_password": "1234", "new_password": "Ecruz"})).startswith(
        "New password must be at least")


def test_logout(teacher):
    assert teacher.post("/api/logout").status_code == 200
    assert teacher.get("/api/dashboard").status_code == 401


def test_logged_out_pages_go_to_login(app):
    client = app.test_client()
    for path in ["/", "/dashboard", "/activities", "/classes", "/teachers", "/my-activities"]:
        assert client.get(path).headers["Location"].endswith("/login"), path


def test_deactivated_account_cannot_log_in(admin, app):
    teacher_id = next(user["id"] for user in admin.get("/api/users?role=teacher").get_json()["users"]
                      if user["username"] == "gpascual")
    client = login("gpascual")
    admin.put(f"/api/users/{teacher_id}", json={"active": False})
    assert client.get("/api/dashboard").status_code == 401  # logged out right away
    response = app.test_client().post("/api/login", json={"username": "gpascual", "password": "1234"})
    assert response.status_code == 403


def test_dashboards(admin, teacher):
    data = admin.get("/api/dashboard").get_json()
    assert (data["role"], data["teachers"], data["students"]) == ("admin", 6, 48)
    assert teacher.get("/api/dashboard").get_json()["role"] == "teacher"
    student = login("jdelacruz01").get("/api/dashboard").get_json()
    assert student["role"] == "student" and student["to_do"] == 0
