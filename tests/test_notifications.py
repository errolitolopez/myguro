"""The bell: a student gets a note when a teacher opens, closes or re-opens an activity or releases scores."""

from conftest import assign, login, make_activity, make_class, open_assignment, set_status


def bell(client):
    return client.get("/api/notifications").get_json()


def setup(teacher):
    class_id, students = make_class(teacher)
    activity_id, _ = make_activity(teacher)
    assignment_id = assign(teacher, activity_id, class_id, opened=False)
    return assignment_id, students


def test_opening_closing_reopening_and_releasing_each_make_a_note(teacher):
    assignment_id, students = setup(teacher)
    student = login(students[0]["username"])
    assert bell(student) == {"unread": 0, "notifications": []}  # giving it is not an event: it is not started

    open_assignment(teacher, assignment_id)
    set_status(teacher, assignment_id, "closed")
    open_assignment(teacher, assignment_id)
    teacher.put(f"/api/assignments/{assignment_id}/release", json={"released": True})
    teacher.put(f"/api/assignments/{assignment_id}/release", json={"released": False})  # hiding says nothing

    data = bell(student)
    assert data["unread"] == 4 and len(data["notifications"]) == 4
    newest = data["notifications"][0]
    assert newest["text"] == "Your score for Early Eastern Philosophy is ready."
    assert newest["link"] == f"/my-activities/{assignment_id}" and newest["read"] is False
    assert data["notifications"][-1]["text"].startswith("Early Eastern Philosophy is now open.")


def test_reading_one_or_all_and_only_your_own(teacher):
    assignment_id, students = setup(teacher)
    open_assignment(teacher, assignment_id)
    set_status(teacher, assignment_id, "closed")
    first, second = login(students[0]["username"]), login(students[1]["username"])
    notes = bell(first)["notifications"]

    assert first.post(f"/api/notifications/{notes[0]['id']}/read").status_code == 200
    assert bell(first)["unread"] == 1
    second.post(f"/api/notifications/{notes[1]['id']}/read")  # someone else's note: nothing changes
    assert bell(first)["unread"] == 1
    first.post("/api/notifications/read-all")
    assert bell(first)["unread"] == 0 and bell(second)["unread"] == 2


def test_excluded_students_get_nothing_and_only_students_have_a_bell(teacher):
    assignment_id, students = setup(teacher)
    teacher.put(f"/api/assignments/{assignment_id}/students/{students[0]['id']}/excluded", json={"excluded": True})
    open_assignment(teacher, assignment_id)
    assert bell(login(students[0]["username"]))["unread"] == 0
    assert bell(login(students[1]["username"]))["unread"] == 1
    assert teacher.get("/api/notifications").status_code == 403
    page = login(students[1]["username"]).get("/dashboard").get_data(as_text=True)
    assert 'id="bell-button"' in page and 'id="bell-button"' not in teacher.get("/dashboard").get_data(as_text=True)


def test_the_note_is_in_the_language_the_student_chose(teacher):
    assignment_id, students = setup(teacher)
    open_assignment(teacher, assignment_id)
    student = login(students[0]["username"])
    student.set_cookie("myguro-lang", "tl")
    assert bell(student)["notifications"][0]["text"] == "Bukas na ang Early Eastern Philosophy. Puwede mo na itong sagutan."


def test_the_bell_shows_only_the_newest_twenty(teacher):
    assignment_id, students = setup(teacher)
    for _ in range(30):  # open + close = 2 notes each time
        open_assignment(teacher, assignment_id)
        set_status(teacher, assignment_id, "closed")
    from myguro.domain.notifications import LIST_LIMIT
    assert len(bell(login(students[0]["username"]))["notifications"]) == LIST_LIMIT
