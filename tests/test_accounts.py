"""Admin: teacher and student accounts."""

from conftest import error, login


def test_create_teacher_with_generated_password(admin, app):
    response = admin.post("/api/users", json={"role": "teacher", "name": "  Maria   Santos ", "username": "MSantos"})
    assert response.status_code == 201
    data = response.get_json()
    assert data["user"]["name"] == "Maria Santos" and data["user"]["username"] == "msantos"
    assert len(data["temp_password"]) == 10
    client = app.test_client()
    assert client.post("/api/login", json={"username": "msantos", "password": data["temp_password"]}) \
        .get_json()["must_change_password"] is True


def test_account_rules(admin):
    assert error(admin.post("/api/users", json={"role": "teacher", "username": "abc"})) == "Name is required."
    assert error(admin.post("/api/users", json={"role": "teacher", "name": "X", "username": "a b"})).startswith(
        "Username must be")
    assert error(admin.post("/api/users", json={"role": "teacher", "name": "X", "username": "ecruz"})) == \
        'The username "ecruz" is already taken.'
    assert error(admin.post("/api/users", json={"role": "teacher", "name": "X", "username": "xyz",
                                                "password": "short"})).startswith("Password must be")
    assert error(admin.post("/api/users", json={"role": "admin", "name": "X", "username": "xyz"})) == "Unknown role."


def test_student_grade_and_section(admin):
    response = admin.post("/api/users", json={"role": "student", "name": "New Kid", "username": "newkid",
                                              "grade": "Grade 9", "section": "rizal "})
    student = response.get_json()["user"]
    assert (student["grade"], student["section"]) == ("Grade 9", "Rizal")  # existing spelling reused
    assert error(admin.post("/api/users", json={"role": "student", "name": "X", "username": "xx1",
                                                "grade": "Grade 13"})) == "Choose a grade from the list."
    updated = admin.put(f"/api/users/{student['id']}", json={"section": ""}).get_json()["user"]
    assert (updated["grade"], updated["section"]) == ("Grade 9", "")


def test_teacher_ignores_grade(admin):
    teacher = admin.post("/api/users", json={"role": "teacher", "name": "T", "username": "tt1",
                                             "grade": "Grade 9"}).get_json()["user"]
    assert teacher["grade"] == ""


def test_list_rename_reset_deactivate(admin, app):
    students = admin.get("/api/users?role=student").get_json()["users"]
    assert len(students) == 48 and "classes" in students[0]
    student = students[0]
    assert admin.put(f"/api/users/{student['id']}", json={"name": "Renamed"}).get_json()["user"]["name"] == "Renamed"
    new_password = admin.put(f"/api/users/{student['id']}", json={"reset_password": True}).get_json()["temp_password"]
    assert app.test_client().post("/api/login", json={"username": student["username"], "password": "1234"}) \
        .status_code == 401
    assert app.test_client().post("/api/login", json={"username": student["username"], "password": new_password}) \
        .status_code == 200
    assert admin.put(f"/api/users/{student['id']}", json={"active": False}).get_json()["user"]["active"] is False


def test_admin_account_cannot_be_edited(admin):
    assert admin.put("/api/users/1", json={"active": False}).status_code == 404


def test_only_admin_manages_accounts(teacher):
    assert teacher.get("/api/users").status_code == 403
    assert teacher.post("/api/users", json={"role": "student", "name": "X", "username": "xyz"}).status_code == 403
    assert login("jdelacruz01").get("/api/users").status_code == 403
