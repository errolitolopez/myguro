"""Maintenance mode: while the admin has it on, everyone but the admin gets the maintenance page."""

from conftest import PASSWORD, flask_app, login

NOTE = "Back at 3 PM. We are updating MyGuro."


def turn(admin, enabled, message=""):
    return admin.put("/api/settings", json={"maintenance": {"enabled": enabled, "message": message}})


def test_it_is_off_by_default(admin, teacher):
    assert admin.get("/api/settings").get_json()["settings"]["maintenance"]["enabled"] is False
    assert teacher.get("/dashboard").status_code == 200


def test_everyone_but_the_admin_gets_the_maintenance_page(admin, teacher, supervisor):
    student = login("jdelacruz01")
    assert turn(admin, True, NOTE).status_code == 200
    for client in (teacher, student, supervisor, flask_app.test_client()):
        page = client.get("/dashboard")
        assert page.status_code == 503 and NOTE in page.get_data(as_text=True)
        assert page.headers["Retry-After"]
    assert flask_app.test_client().get("/forgot-password").status_code == 503
    for client in (teacher, student):
        answer = client.get("/api/classes" if client is teacher else "/api/my-activities")
        assert answer.status_code == 503 and answer.get_json() == {"error": NOTE, "maintenance": True}
    # Not even the admin's own API is open to a teacher
    assert teacher.put("/api/settings", json={"maintenance": {"enabled": False, "message": ""}}).status_code == 503


def test_the_admin_keeps_working_and_sees_a_banner(admin):
    turn(admin, True)
    page = admin.get("/dashboard")
    assert page.status_code == 200 and "Maintenance mode is on" in page.get_data(as_text=True)
    assert admin.get("/api/classes").status_code != 503
    assert admin.get("/settings").status_code == 200


def test_the_login_page_stays_open_and_the_admin_can_sign_in(admin):
    turn(admin, True)
    anonymous = flask_app.test_client()
    assert anonymous.get("/login").status_code == 200
    assert anonymous.get("/static/css/glass.css").status_code == 200
    assert anonymous.post("/api/login", json={"username": "admin", "password": "adminpass1"}).status_code == 200


def test_a_non_admin_can_sign_in_and_lands_on_the_maintenance_page(admin):
    """The login itself works (no confusing error on the form); the page they are sent to is the maintenance page."""
    turn(admin, True, NOTE)
    client = flask_app.test_client()
    answer = client.post("/api/login", json={"username": "ecruz", "password": PASSWORD})
    assert answer.status_code == 200 and answer.get_json()["ok"] is True
    page = client.get("/dashboard")  # where login.js sends a person next
    assert page.status_code == 503 and NOTE in page.get_data(as_text=True)
    assert 'id="logout-button"' in page.get_data(as_text=True)  # a signed-in person can log out from it
    # A first login (temporary password) is sent to /change-password: also the maintenance page
    assert client.get("/change-password").status_code == 503
    # A wrong password is still a wrong password
    assert flask_app.test_client().post("/api/login", json={"username": "ecruz", "password": "nope"}).status_code == 401


def test_signed_in_people_are_not_logged_out_and_work_again_when_it_is_off(admin, teacher):
    turn(admin, True)
    assert teacher.get("/dashboard").status_code == 503
    assert turn(admin, False).status_code == 200
    assert teacher.get("/dashboard").status_code == 200  # the same session


def test_a_blocked_person_can_still_log_out(admin, teacher):
    turn(admin, True)
    assert teacher.post("/api/logout").status_code == 200
    assert teacher.get("/dashboard").status_code == 503
    assert teacher.get("/login").status_code == 200


def test_the_default_text_is_used_without_a_note_and_follows_the_language(admin, teacher):
    turn(admin, True, "")
    english = teacher.get("/dashboard").get_data(as_text=True)
    assert "MyGuro is down for maintenance." in english
    teacher.set_cookie("myguro-lang", "tl")
    assert "Naka-maintenance ang MyGuro" in teacher.get("/dashboard").get_data(as_text=True)


def test_turning_it_on_and_off_is_logged(admin):
    turn(admin, True, NOTE)
    turn(admin, False, NOTE)
    entries = admin.get("/api/log?category=settings&per_page=100").get_json()["entries"]
    actions = [e["action"] for e in reversed(entries)]
    # The first save also set the note (its own entry); the second only turned it off
    assert actions == ["settings.maintenance_on", "settings.changed", "settings.maintenance_off"]


def test_bad_input_is_refused_and_nothing_changes(admin):
    assert admin.put("/api/settings", json={"maintenance": {"enabled": "yes"}}).status_code == 400
    assert admin.put("/api/settings", json={"maintenance": "on"}).status_code == 400
    assert turn(admin, True, "x" * 201).status_code == 400
    assert admin.get("/api/settings").get_json()["settings"]["maintenance"]["enabled"] is False


def test_the_admin_settings_page_has_the_maintenance_card_and_others_do_not(admin, teacher):
    assert 'id="maintenance-form"' in admin.get("/system-settings").get_data(as_text=True)
    assert 'id="maintenance-form"' not in admin.get("/settings").get_data(as_text=True)
    assert teacher.get("/system-settings").status_code == 302  # sent to their dashboard
