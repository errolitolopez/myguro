"""Admin: teacher and student accounts. Names are Last name, First name, Middle initial."""

from conftest import error, login


def person(last="Santos", first="Maria", middle="", **extra):
    return {"last_name": last, "first_name": first, "middle_initial": middle, **extra}


def test_create_teacher_with_generated_password(admin, app):
    response = admin.post("/api/users", json=person("  Dela  Cruz ", " Maria   Clara", "m.", role="teacher",
                                                    username="MDelaCruz"))
    assert response.status_code == 201
    user = response.get_json()["user"]
    assert (user["last_name"], user["first_name"], user["middle_initial"]) == ("Dela Cruz", "Maria Clara", "M")
    assert user["name"] == "Dela Cruz, Maria Clara M." and user["username"] == "mdelacruz"
    password = response.get_json()["temp_password"]
    assert len(password) == 10
    assert app.test_client().post("/api/login", json={"username": "mdelacruz", "password": password}) \
        .get_json()["must_change_password"] is True


def test_name_can_be_sent_as_one_text_with_commas(admin):
    user = admin.post("/api/users", json={"role": "student", "name": "Altamerano, Rian Joshua, J",
                                          "username": "raltamerano"}).get_json()["user"]
    assert (user["last_name"], user["first_name"], user["middle_initial"]) == ("Altamerano", "Rian Joshua", "J")
    assert user["name"] == "Altamerano, Rian Joshua J."
    assert error(admin.post("/api/users", json={"role": "student", "name": "Rian Joshua Altamerano",
                                                "username": "rja"})) == \
        "Write the name as Last name, First name (e.g. Altamerano, Rian Joshua)."


def test_name_rules(admin):
    post = lambda **data: error(admin.post("/api/users", json={"role": "teacher", "username": "xyz", **data}))
    assert post(**person(last="")) == "Last name is required."
    assert post(**person(first=" ")) == "First name is required."
    assert post(**person(last="x" * 51)) == "Last name can be at most 50 characters."
    assert post(**person(middle="7")) == "The middle initial must be a letter."


def test_middle_name_becomes_initial(admin):
    user = admin.post("/api/users", json=person(middle="mendoza", role="student", username="msantos2")) \
        .get_json()["user"]
    assert user["middle_initial"] == "M" and user["name"] == "Santos, Maria M."


def test_account_rules(admin):
    post = lambda **data: error(admin.post("/api/users", json={"role": "teacher", **person(), **data}))
    assert post(username="a b").startswith("Username must be")
    assert post(username="ecruz") == 'The username "ecruz" is already taken.'
    assert post(username="xyz", password="short").startswith("Password must be")
    assert post(username="xyz", role="admin") == "Unknown role."


def test_student_grade_and_section(admin):
    student = admin.post("/api/users", json=person("Kid", "New", role="student", username="newkid",
                                                   grade="Grade 9", section="rizal ")).get_json()["user"]
    assert (student["grade"], student["section"]) == ("Grade 9", "Rizal")  # existing spelling reused
    assert error(admin.post("/api/users", json=person(role="student", username="xx1", grade="Grade 13"))) == \
        "Choose a grade from the list."
    updated = admin.put(f"/api/users/{student['id']}", json={"section": ""}).get_json()["user"]
    assert (updated["grade"], updated["section"]) == ("Grade 9", "")


def test_teacher_ignores_grade(admin):
    teacher = admin.post("/api/users", json=person(role="teacher", username="tt1", grade="Grade 9")).get_json()["user"]
    assert teacher["grade"] == ""


def test_list_is_paged(admin):
    data = admin.get("/api/users?role=student").get_json()
    assert (data["page"], data["pages"], data["per_page"], data["total"]) == (1, 3, 20, 48)
    assert (data["all_count"], data["active_count"]) == (48, 48)
    assert len(data["users"]) == 20 and "classes" in data["users"][0]
    names = [student["name"] for page in (1, 2, 3)
             for student in admin.get(f"/api/users?role=student&page={page}").get_json()["users"]]
    assert len(names) == 48 and len(set(names)) == 48
    assert names == sorted(names, key=str.casefold)  # by last name, across pages
    last = admin.get("/api/users?role=student&page=3").get_json()
    assert len(last["users"]) == 8
    assert admin.get("/api/users?role=student&page=99").get_json()["page"] == 3  # past the end: last page
    assert admin.get("/api/users?role=student&page=abc").get_json()["page"] == 1
    assert len(admin.get("/api/users?role=student&per_page=50").get_json()["users"]) == 48
    assert admin.get("/api/users?role=student&per_page=500").get_json()["per_page"] == 100  # capped


def test_list_search_and_grade_filter(admin):
    found = admin.get("/api/users?role=student&q=rizal").get_json()  # section
    assert found["total"] == 6 and all(user["section"] == "Rizal" for user in found["users"])
    assert found["all_count"] == 48
    assert admin.get("/api/users?role=student&q=jdelacruz01").get_json()["total"] == 1  # username
    assert admin.get("/api/users?role=student&q=%25").get_json()["total"] == 0  # % is not a wildcard
    assert admin.get("/api/users?role=student&grade=Grade+12").get_json()["total"] == 12
    assert admin.get("/api/users?role=student&grade=Grade+12&q=stem").get_json()["total"] == 6
    admin.post("/api/users", json=person("Irregular", "Ira", role="student", username="iirregular"))
    no_grade = admin.get("/api/users?role=student&grade=").get_json()
    assert [user["username"] for user in no_grade["users"]] == ["iirregular"]
    teachers = admin.get("/api/users?role=teacher").get_json()
    assert teachers["total"] == 6 and teachers["pages"] == 1


def test_deactivated_go_last(admin):
    first = admin.get("/api/users?role=student").get_json()["users"][0]
    admin.put(f"/api/users/{first['id']}", json={"active": False})
    data = admin.get("/api/users?role=student&page=3").get_json()
    assert data["users"][-1]["id"] == first["id"] and data["active_count"] == 47


def test_list_rename_reset_deactivate(admin, app):
    student = admin.get("/api/users?role=student").get_json()["users"][0]
    renamed = admin.put(f"/api/users/{student['id']}", json={"first_name": "Renamed"}).get_json()["user"]
    assert renamed["first_name"] == "Renamed" and renamed["last_name"] == student["last_name"]
    assert renamed["name"].startswith(f"{student['last_name']}, Renamed")
    assert error(admin.put(f"/api/users/{student['id']}", json={"last_name": ""})) == "Last name is required."
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
    assert teacher.post("/api/users", json={"role": "student", **person(), "username": "xyz"}).status_code == 403
    assert login("jdelacruz01").get("/api/users").status_code == 403
