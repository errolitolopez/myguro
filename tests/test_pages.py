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
                 f"/results/{assignment_id}"]:
        assert teacher.get(path).status_code == 200, path
    for path in ["/dashboard", "/my-activities", f"/my-activities/{assignment_id}"]:
        assert student.get(path).status_code == 200, path

    # Wrong role -> back to the dashboard
    for client, path in [(teacher, "/teachers"), (student, "/activities"), (student, f"/results/{assignment_id}"),
                         (admin, "/classes"), (teacher, "/my-activities")]:
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
