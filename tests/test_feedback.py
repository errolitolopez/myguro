"""Feedback: teachers and students rate MyGuro from 1 to 5; only the admin reads the totals."""

import pytest

from conftest import login


ALL_FIVE = {"easy": 4, "read": 5, "clear": 3, "look": 4, "overall": 5}


def test_a_student_sends_feedback_once(admin):
    student = login("jdelacruz01")
    first = student.get("/api/feedback").get_json()
    assert [question["key"] for question in first["questions"]] == ["easy", "read", "clear", "look", "overall"]
    assert first["submitted"] is False

    assert student.put("/api/feedback", json={"ratings": ALL_FIVE}).get_json() == {"submitted": True}
    assert student.get("/api/feedback").get_json()["submitted"] is True
    # A second try, even with other numbers, is refused and changes nothing
    again = student.put("/api/feedback", json={"ratings": {key: 1 for key in ALL_FIVE}})
    assert again.status_code == 400 and "already" in again.get_json()["error"]
    assert admin.get("/api/feedback/summary").get_json()["questions"][0]["average"] == 4.0


def test_every_question_must_be_rated(admin):
    student = login("jdelacruz01")
    response = student.put("/api/feedback", json={"ratings": {"easy": 4, "overall": 5}})
    assert response.status_code == 400 and "every question" in response.get_json()["error"]
    assert student.get("/api/feedback").get_json()["submitted"] is False  # nothing was saved


@pytest.mark.parametrize("ratings", [None, {}, {"easy": 0}, {"easy": 6}, {"easy": "5"}, {"easy": True},
                                     {"easy": 4.5}, {"nope": 3}, [("easy", 3)]])
def test_bad_ratings_are_refused(admin, ratings):
    response = login("jdelacruz01").put("/api/feedback", json={"ratings": ratings})
    assert response.status_code == 400 and response.get_json()["error"]
    assert admin.get("/api/feedback/summary").get_json()["respondents"] == 0


def test_admin_and_supervisor_do_not_rate(admin, supervisor):
    for client in (admin, supervisor):
        assert client.get("/api/feedback").status_code == 403
        assert client.put("/api/feedback", json={"ratings": ALL_FIVE}).status_code == 403


def test_only_the_admin_reads_the_totals(admin, teacher, supervisor):
    for client in (teacher, supervisor, login("jdelacruz01")):
        assert client.get("/api/feedback/summary").status_code == 403


def test_totals_average_and_counts_by_group(admin, teacher):
    login("jdelacruz01").put("/api/feedback", json={"ratings": {**ALL_FIVE, "easy": 5, "overall": 4}})
    other = next(user["username"] for user in admin.get("/api/users?role=student").get_json()["users"]
                 if user["username"] != "jdelacruz01")
    login(other).put("/api/feedback", json={"ratings": {**ALL_FIVE, "easy": 4}})
    teacher.put("/api/feedback", json={"ratings": {**ALL_FIVE, "easy": 3}})

    everyone = admin.get("/api/feedback/summary").get_json()
    assert everyone["respondents"] == 3
    easy = everyone["questions"][0]
    assert (easy["key"], easy["count"], easy["average"], easy["counts"]) == ("easy", 3, 4.0, [0, 0, 1, 1, 1])
    unrated = everyone["questions"][1]
    assert unrated["key"] == "read" and unrated["count"] == 3 and unrated["average"] == 5.0

    students = admin.get("/api/feedback/summary?role=student").get_json()
    assert students["respondents"] == 2 and students["questions"][0]["average"] == 4.5
    teachers = admin.get("/api/feedback/summary?role=teacher").get_json()
    assert teachers["respondents"] == 1 and teachers["questions"][0]["average"] == 3.0
    assert admin.get("/api/feedback/summary?role=admin").status_code == 400


def test_the_totals_never_name_anyone(admin):
    login("jdelacruz01").put("/api/feedback", json={"ratings": ALL_FIVE})
    text = admin.get("/api/feedback/summary").get_data(as_text=True).lower()
    assert "jdelacruz01" not in text and "cruz" not in text


def test_rating_is_not_written_to_the_activity_log(admin, supervisor):
    login("jdelacruz01").put("/api/feedback", json={"ratings": ALL_FIVE})
    summaries = " ".join(entry["summary"] for entry in admin.get("/api/log?per_page=100").get_json()["entries"])
    assert "feedback" not in summaries.lower() and "rating" not in summaries.lower()


def test_feedback_page_per_role(admin, teacher, supervisor):
    assert 'id="feedback-form"' in login("jdelacruz01").get("/feedback").get_data(as_text=True)
    assert 'id="feedback-form"' in teacher.get("/feedback").get_data(as_text=True)
    assert 'id="feedback-results"' in admin.get("/feedback").get_data(as_text=True)
    assert supervisor.get("/feedback").headers["Location"].endswith("/dashboard")


POPUP = 'id="feedback-modal"'


def test_popup_asks_once_per_login_until_feedback_is_sent(admin, teacher):
    student = login("jdelacruz01")
    assert POPUP in student.get("/dashboard").get_data(as_text=True)  # the default is once each login
    assert POPUP not in student.get("/dashboard").get_data(as_text=True)  # not again in the same login
    assert POPUP in login("jdelacruz01").get("/dashboard").get_data(as_text=True)  # a new login asks again
    assert POPUP in teacher.get("/dashboard").get_data(as_text=True)  # teachers too

    sender = login("jdelacruz01")
    sender.put("/api/feedback", json={"ratings": ALL_FIVE})
    assert POPUP not in login("jdelacruz01").get("/dashboard").get_data(as_text=True)  # sent: never again


def test_popup_is_not_for_admin_supervisor_or_the_feedback_page(admin, supervisor):
    assert POPUP not in admin.get("/dashboard").get_data(as_text=True)
    assert POPUP not in supervisor.get("/log").get_data(as_text=True)
    student = login("jdelacruz01")
    assert POPUP not in student.get("/feedback").get_data(as_text=True)
    assert POPUP in student.get("/dashboard").get_data(as_text=True)  # the feedback page did not use up the ask


def test_popup_never_opens_on_the_answer_page(admin, teacher):
    from conftest import assign, make_activity, make_class
    class_id, students = make_class(teacher)
    activity_id, _ = make_activity(teacher)
    assignment_id = assign(teacher, activity_id, class_id)
    teacher.put(f"/api/assignments/{assignment_id}/status", json={"status": "open"})
    student = login(students[0]["username"])
    assert POPUP not in student.get(f"/my-activities/{assignment_id}").get_data(as_text=True)
    assert POPUP in student.get("/dashboard").get_data(as_text=True)


def test_admin_chooses_when_the_popup_opens(admin):
    assert admin.get("/api/settings").get_json()["settings"]["feedback_popup"] == "login"
    assert admin.put("/api/settings", json={"feedback_popup": "nope"}).status_code == 400

    assert admin.put("/api/settings", json={"feedback_popup": "off"}).get_json()["settings"]["feedback_popup"] == "off"
    assert POPUP not in login("jdelacruz01").get("/dashboard").get_data(as_text=True)

    admin.put("/api/settings", json={"feedback_popup": "daily"})
    student = login("jdelacruz01")
    assert POPUP in student.get("/dashboard").get_data(as_text=True)
    assert POPUP not in student.get("/dashboard").get_data(as_text=True)  # once a day
