"""Admin: making new temporary passwords for many students at once (the first ones were not downloaded)."""

from conftest import error, login


def new_student(admin, username, password="first-pass"):
    response = admin.post("/api/users", json={
        "role": "student", "last_name": "Fresh", "first_name": username, "username": username,
        "grade": "Grade 7", "section": "Pass", "password": password,
    })
    assert response.status_code == 201
    return response.get_json()["user"]["id"]


def reset(admin, **data):
    return admin.post("/api/users/batch-reset-passwords", json=data)


def try_login(username, password):
    from conftest import flask_app

    return flask_app.test_client().post("/api/login", json={"username": username, "password": password})


def test_new_passwords_replace_the_old_and_must_be_changed(admin):
    ids = [new_student(admin, "pass_one"), new_student(admin, "pass_two")]
    admin.post("/api/users/batch-activate", json={"user_ids": ids})  # new students can't log in until activated
    data = reset(admin, user_ids=ids).get_json()
    assert [student["username"] for student in data["students"]] == ["pass_one", "pass_two"]
    assert all(student["grade"] == "Grade 7" and student["section"] == "Pass" for student in data["students"])
    passwords = {student["username"]: student["password"] for student in data["students"]}
    assert all(len(password) >= 6 for password in passwords.values()) and len(set(passwords.values())) == 2

    for username, password in passwords.items():
        assert try_login(username, "first-pass").status_code == 401  # the old one is gone
        response = try_login(username, password)
        assert response.status_code == 200 and response.get_json()["must_change_password"] is True


def test_match_selects_every_student_of_a_search(admin):
    new_student(admin, "pass_one")
    new_student(admin, "pass_two")
    data = reset(admin, match={"section": "Pass"}).get_json()
    assert len(data["students"]) == 2


def test_the_log_has_one_entry_and_no_password(admin):
    ids = [new_student(admin, "pass_one"), new_student(admin, "pass_two")]
    passwords = [student["password"] for student in reset(admin, user_ids=ids).get_json()["students"]]
    entries = [item for item in admin.get("/api/log?category=accounts&per_page=100").get_json()["entries"]
               if item["action"] == "account.batch_passwords_reset"]
    assert len(entries) == 1 and "2 students" in entries[0]["summary"]
    assert not any(password in str(entries[0]) for password in passwords)


def test_rules(admin, teacher):
    new_student(admin, "pass_one")
    assert error(reset(admin, user_ids=[])) == "Choose at least one student."
    teacher_id = admin.get("/api/users?role=teacher").get_json()["users"][0]["id"]
    assert error(reset(admin, user_ids=[teacher_id])) == "Only students can be regenerated here."
    assert teacher.post("/api/users/batch-reset-passwords", json={"user_ids": [1]}).status_code == 403
