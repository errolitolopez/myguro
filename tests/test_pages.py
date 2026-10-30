"""Every page opens for the right role and sends others away."""

from conftest import assign, login, make_activity, make_class


def test_pages_per_role(admin, teacher):
    class_id, students = make_class(teacher)
    activity_id, _ = make_activity(teacher)
    assignment_id = assign(teacher, activity_id, class_id)
    student = login(students[0]["username"])

    for path in ["/dashboard", "/teachers", "/students", "/change-password"]:
        assert admin.get(path).status_code == 200, path
    for path in ["/dashboard", "/activities", f"/activities/{activity_id}", "/classes", f"/classes/{class_id}",
                 f"/results/{assignment_id}", f"/results/{assignment_id}/students/{students[0]['id']}"]:
        assert teacher.get(path).status_code == 200, path
    for path in ["/dashboard", "/my-activities", f"/my-activities/{assignment_id}"]:
        assert student.get(path).status_code == 200, path

    # Wrong role -> back to the dashboard
    for client, path in [(teacher, "/teachers"), (student, "/activities"), (student, f"/results/{assignment_id}"),
                         (student, f"/results/{assignment_id}/students/{students[0]['id']}"), (admin, "/classes"), (teacher, "/my-activities")]:
        assert client.get(path).headers["Location"].endswith("/dashboard"), path


def test_navbar_per_role(admin, teacher):
    assert 'href="/teachers"' in admin.get("/dashboard").get_data(as_text=True)
    page = teacher.get("/dashboard").get_data(as_text=True)
    assert 'href="/activities"' in page and 'href="/classes"' in page and 'href="/teachers"' not in page
    assert 'href="/my-activities"' in login("jdelacruz01").get("/dashboard").get_data(as_text=True)


def test_login_page_and_redirects(app, teacher):
    assert app.test_client().get("/login").status_code == 200
    assert teacher.get("/login").headers["Location"].endswith("/dashboard")
    assert teacher.get("/").headers["Location"].endswith("/dashboard")


def test_tip_box_for_teachers_and_students_not_on_answer_page(admin, teacher):
    class_id, students = make_class(teacher)
    activity_id, _ = make_activity(teacher)
    assignment_id = assign(teacher, activity_id, class_id)
    student = login(students[0]["username"])

    assert 'id="tip-box"' not in admin.get("/dashboard").get_data(as_text=True)
    assert 'id="tip-box" class="container d-none" data-role="teacher"' in teacher.get("/dashboard").get_data(as_text=True)
    assert 'data-role="student"' in student.get("/my-activities").get_data(as_text=True)
    assert 'id="tip-box"' not in student.get(f"/my-activities/{assignment_id}").get_data(as_text=True)


def test_a_wrong_address_shows_the_not_found_page_and_an_api_one_answers_json(teacher):
    page = teacher.get("/no-such-page")
    assert page.status_code == 404 and b"Page not found" in page.data
    api = teacher.get("/api/no-such-route")
    assert api.status_code == 404 and api.get_json() == {"error": "Not found."}


def test_dashboard_chart_is_for_teachers_and_students_only(admin, teacher):
    chart = 'id="chart-card"'
    assert chart not in admin.get("/dashboard").get_data(as_text=True)
    teacher_page = teacher.get("/dashboard").get_data(as_text=True)
    assert 'data-role="teacher"' in teacher_page
    # The To check card is a teacher thing too
    assert 'id="to-check-card"' in teacher_page
    assert 'id="to-check-card"' not in login("jdelacruz01").get("/dashboard").get_data(as_text=True)
    page = login("jdelacruz01").get("/dashboard").get_data(as_text=True)
    assert chart in page and 'data-role="student"' in page


def test_every_page_with_the_account_menu_loads_common_js(admin, teacher, supervisor):
    """common.js makes Logout work; a page without it has a dead Logout button."""
    student = login("jdelacruz01")
    for client, path in [(admin, "/display"), (teacher, "/display"), (student, "/display"), (supervisor, "/display"),
                         (admin, "/feedback"), (teacher, "/feedback"), (student, "/feedback")]:
        page = client.get(path).get_data(as_text=True)
        assert 'id="logout-button"' in page and "js/common.js" in page, path


def test_display_page_is_open_to_every_role(admin, teacher, supervisor):
    for client in (admin, teacher, supervisor, login("jdelacruz01")):
        page = client.get("/display").get_data(as_text=True)
        assert "data-theme-select" in page and 'data-reading-select="size"' in page
        assert 'data-reading-switch="tabbar"' in page and 'data-reading-switch="effects"' in page
        # The choices live on this page now, not in the account menu of the other pages
        assert "data-theme-select" not in client.get("/dashboard" if client is not supervisor else "/log").get_data(as_text=True)


def test_a_crash_shows_our_own_page_or_json_and_never_a_traceback(teacher, monkeypatch):
    from myguro.services import SettingsService
    import myguro.web.display as display_page

    def boom(*args, **kwargs):
        raise RuntimeError("secret details")

    monkeypatch.setattr(display_page, "render_template", boom)
    page = teacher.get("/display")
    assert page.status_code == 500 and b"Something went wrong" in page.data and b"Try again" in page.data
    assert b"secret details" not in page.data and b"Traceback" not in page.data

    monkeypatch.setattr(SettingsService, "get", boom)
    api = teacher.get("/api/settings")
    assert api.status_code == 500 and api.get_json() == {"error": "Something went wrong. Please try again."}


def test_a_wrong_method_shows_our_not_allowed_page(teacher):
    page = teacher.post("/dashboard")
    assert page.status_code == 405 and b"Not allowed" in page.data
    assert teacher.post("/api/settings/nothing").status_code == 404


def test_the_error_page_has_a_plain_fallback(app, monkeypatch):
    import myguro.errors as errors

    def boom(*args, **kwargs):
        raise RuntimeError("template is broken")

    monkeypatch.setattr(errors, "render_template", boom)
    with app.test_request_context("/somewhere"):
        body, status = errors.error_response(500, "x", "y", "z")
    assert status == 500 and "Something went wrong" in body and "Traceback" not in body


def test_hidden_chart_tables_do_not_widen_the_page():
    # A table ignores the 1px width and clip of "visually-hidden", so it pushed the page wider than a phone.
    # The class must be on a div around the table.
    for path in ("myguro/templates/_dashboard_chart.html", "myguro/templates/log.html"):
        assert '<table class="visually-hidden"' not in open(path).read()


def test_the_navbar_has_a_quick_theme_menu_before_the_search_button(teacher):
    page = teacher.get("/dashboard").get_data(as_text=True)
    for theme in ("auto", "light", "dark", "darcula", "solarized", "neon"):
        assert f'data-theme-choice="{theme}"' in page
    assert page.index('aria-label="Change theme"') < page.index('id="palette-button"')


def test_the_cookie_notice_is_on_every_page_but_the_answer_page(teacher):
    # The notice only tells about the two cookies the app needs; it asks for nothing.
    from app import app as flask_app

    assert 'id="cookie-notice"' in flask_app.test_client().get("/login").get_data(as_text=True)
    assert 'id="cookie-notice"' in teacher.get("/dashboard").get_data(as_text=True)
    class_id, students = make_class(teacher)
    activity_id, _ = make_activity(teacher)
    assignment_id = assign(teacher, activity_id, class_id)
    student = login(students[0]["username"])
    assert 'id="cookie-notice"' not in student.get(f"/my-activities/{assignment_id}").get_data(as_text=True)
