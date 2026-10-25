"""Admin settings: the order of the grade dropdowns, saved in the database."""

import re

from conftest import error, login, make_class


def grade_options(html, select_id):
    """The option texts of the <select id=...> in a page."""
    select = re.search(rf'<select id="{select_id}".*?</select>', html, re.S).group(0)
    return re.findall(r"<option[^>]*>([^<]*)</option>", select)


def test_default_is_highest_first(admin):
    settings = admin.get("/api/settings").get_json()["settings"]
    assert settings["grades_high_to_low"] is True
    assert settings["grades"][0] == {"name": "Grade 12", "enabled": True}
    assert len(settings["grades"]) == 13 and all(grade["enabled"] for grade in settings["grades"])
    html = admin.get("/students").get_data(as_text=True)
    grades = [grade for grade in grade_options(html, "grade-filter") if grade.startswith(("Grade", "Kinder"))]
    assert grades[0] == "Grade 12" and grades[-1] == "Kinder"


def test_turn_off_saves_and_changes_every_dropdown(admin, teacher):
    response = admin.put("/api/settings", json={"grades_high_to_low": False})
    assert response.get_json()["settings"]["grades_high_to_low"] is False
    # Saved in the database: a new session sees it too
    assert login("admin", "adminpass1").get("/api/settings").get_json()["settings"]["grades_high_to_low"] is False

    class_id, _ = make_class(teacher)
    page = teacher.get(f"/classes/{class_id}").get_data(as_text=True)
    grades = grade_options(page, "grade-filter")
    assert grades[:2] == ["All grades", "Kinder"] and grades[-1] == "Grade 12"

    admin.put("/api/settings", json={"grades_high_to_low": True})
    page = teacher.get(f"/classes/{class_id}").get_data(as_text=True)
    assert grade_options(page, "grade-filter")[:2] == ["All grades", "Grade 12"]


def test_only_admin_changes_it(teacher):
    assert teacher.put("/api/settings", json={"grades_high_to_low": False}).status_code == 403
    assert teacher.get("/settings").status_code == 302  # sent back to the dashboard


def test_value_must_be_on_or_off(admin):
    assert error(admin.put("/api/settings", json={"grades_high_to_low": "no"})) == "Choose on or off."
    assert error(admin.put("/api/settings", json={"disabled_grades": ["Grade 99"]})) == \
        "Choose grades from the list."
    assert error(admin.put("/api/settings", json={"disabled_grades": "Kinder"})) == "Choose grades from the list."
    assert admin.get("/api/settings").get_json()["settings"]["grades_high_to_low"] is True
    assert admin.get("/settings").status_code == 200


def new_student(admin, grade, username="jtest"):
    return admin.post("/api/users", json={"role": "student", "last_name": "Test", "first_name": "Juan",
                                          "username": username, "grade": grade, "section": "Rizal"})


def test_disabled_grade_hidden_and_refused(admin, teacher):
    admin.put("/api/settings", json={"disabled_grades": ["Kinder", "Grade 1"]})
    settings = admin.get("/api/settings").get_json()["settings"]
    assert [g["name"] for g in settings["grades"] if not g["enabled"]] == ["Grade 1", "Kinder"]

    page = admin.get("/students").get_data(as_text=True)
    assert "Kinder" not in grade_options(page, "add-grade") and "Grade 1" not in grade_options(page, "add-grade")
    assert "Kinder" not in grade_options(page, "batch-grade")
    # the Students filter still lists them, so students there can be found and moved
    assert "Kinder" in grade_options(page, "grade-filter")

    assert error(new_student(admin, "Kinder")) == "Kinder is disabled. Choose another grade (Settings page)."
    assert new_student(admin, "Grade 2").status_code == 201


def test_student_keeps_a_grade_that_gets_disabled(admin):
    student = new_student(admin, "Grade 7").get_json()["user"]
    admin.put("/api/settings", json={"disabled_grades": ["Grade 7"]})
    # changing only the section keeps the grade
    response = admin.put(f"/api/users/{student['id']}", json={"grade": "Grade 7", "section": "Luna"})
    assert response.status_code == 200 and response.get_json()["user"]["grade"] == "Grade 7"
    # moving someone into it is refused, moving out works
    other = new_student(admin, "Grade 8", "jother").get_json()["user"]
    assert admin.put(f"/api/users/{other['id']}", json={"grade": "Grade 7"}).status_code == 400
    assert admin.put(f"/api/users/{student['id']}", json={"grade": "Grade 8"}).status_code == 200
    assert admin.put("/api/users/batch", json={"user_ids": [other["id"]], "grade": "Grade 7"}).status_code == 400


SUPPORT = {"enabled": True, "url": "https://ko-fi.com/myguro", "message": "Help pay for hosting",
           "label": "Donate", "gcash_number": "", "gcash_name": ""}


def test_support_link_off_by_default_and_for_staff_only(admin, teacher):
    assert admin.get("/api/settings").get_json()["settings"]["support"]["enabled"] is False
    assert "ko-fi.com" not in teacher.get("/dashboard").get_data(as_text=True)

    saved = admin.put("/api/settings", json={"support": SUPPORT}).get_json()["settings"]["support"]
    assert {key: saved[key] for key in SUPPORT} == SUPPORT
    for client in (admin, teacher):
        page = client.get("/dashboard").get_data(as_text=True)
        assert "https://ko-fi.com/myguro" in page and "Help pay for hosting" in page and "Donate" in page
        assert 'id="support-modal"' in page and "Open Ko-fi" in page and "data-number" not in page
    # students never see it
    class_id, students = make_class(teacher)
    teacher.post(f"/api/classes/{class_id}/students", json={"student_ids": []})
    admin.put(f"/api/users/{students[0]['id']}", json={"active": True})
    assert "ko-fi.com" not in login(students[0]["username"]).get("/dashboard").get_data(as_text=True)

    admin.put("/api/settings", json={"support": {**SUPPORT, "enabled": False}})
    assert "ko-fi.com" not in teacher.get("/dashboard").get_data(as_text=True)
    # the link and text are kept while it is off
    assert admin.get("/api/settings").get_json()["settings"]["support"]["url"] == "https://ko-fi.com/myguro"


def test_support_link_checked(admin):
    put = lambda **changes: error(admin.put("/api/settings", json={"support": {**SUPPORT, **changes}}))
    assert put(url="") == "Add a link or a GCash number before turning the support link on."
    assert put(gcash_number="12345") == "GCash number must be a mobile number like 0917 123 4567."
    assert put(gcash_name="x" * 61) == "GCash name can be at most 60 characters."
    assert put(url="javascript:alert(1)") == "Link must be a web address starting with http:// or https://."
    assert put(url="ko-fi.com/me") == "Link must be a web address starting with http:// or https://."
    assert put(label="x" * 31) == "Button text can be at most 30 characters."
    # empty text uses the defaults
    saved = admin.put("/api/settings", json={"support": {**SUPPORT, "message": "", "label": ""}}).get_json()
    assert saved["settings"]["support"]["label"] == "Support MyGuro"


def test_gcash_number_shown_to_staff(admin, teacher):
    support = {**SUPPORT, "url": "", "gcash_number": "+63 917-123-4567", "gcash_name": "Juan D."}
    saved = admin.put("/api/settings", json={"support": support}).get_json()["settings"]["support"]
    assert saved["gcash_number"] == "09171234567" and saved["gcash_display"] == "0917 123 4567"
    page = teacher.get("/dashboard").get_data(as_text=True)
    assert "0917 123 4567" in page and "Juan D." in page and 'data-number="09171234567"' in page
    assert "ko-fi.com" not in page and "Open Ko-fi" not in page  # no Ko-fi link set


def test_footer_on_every_page(admin):
    anonymous = admin.application.test_client()
    assert "free, non-profit tool for schools" in anonymous.get("/login").get_data(as_text=True)
    assert "free, non-profit tool for schools" in admin.get("/dashboard").get_data(as_text=True)


def test_icons_are_served(admin):
    anonymous = admin.application.test_client()
    assert "img/favicon.svg" in anonymous.get("/login").get_data(as_text=True)
    assert anonymous.get("/favicon.ico").status_code == 302
    for name in ("favicon.svg", "favicon.ico", "favicon-32.png", "apple-touch-icon.png", "mark.svg"):
        assert anonymous.get(f"/static/img/{name}").status_code == 200


def test_support_popup_for_teachers_only_as_often_as_chosen(admin, teacher):
    marker = "bootstrap.Modal.getOrCreateInstance(document.getElementById(\"support-modal\")).show()"
    shows = lambda client: marker in client.get("/dashboard").get_data(as_text=True)
    put = lambda popup: admin.put("/api/settings", json={"support": {**SUPPORT, "popup": popup}})

    # off by default, even with the support link on
    admin.put("/api/settings", json={"support": SUPPORT})
    assert admin.get("/api/settings").get_json()["settings"]["support"]["popup"] == "off"
    assert not shows(teacher)

    # once per login: opens on the first page only, and again after a new login
    put("login")
    assert shows(teacher) and not shows(teacher)
    assert not shows(admin)  # admin has the footer button only
    assert shows(login("ecruz"))

    # on every page
    put("always")
    assert shows(teacher) and shows(teacher)

    # the support link off: no pop-up
    admin.put("/api/settings", json={"support": {**SUPPORT, "popup": "always", "enabled": False}})
    assert not shows(teacher)

    # students never see it
    put("always")
    class_id, students = make_class(teacher)
    assert not shows(login(students[0]["username"]))


def test_support_popup_mode_checked(admin):
    response = admin.put("/api/settings", json={"support": {**SUPPORT, "popup": "sometimes"}})
    assert error(response) == "Choose when to show the pop-up from the list."
