"""Feedback: teachers and students rate MyGuro from 1 to 5; only the admin reads the totals."""

import pytest

from conftest import login


def test_a_student_rates_and_can_change_it(admin):
    student = login("jdelacruz01")
    first = student.get("/api/feedback").get_json()
    assert [question["key"] for question in first["questions"]] == ["easy", "read", "clear", "look", "overall"]
    assert first["ratings"] == {}

    assert student.put("/api/feedback", json={"ratings": {"easy": 4, "overall": 5}}).status_code == 200
    # Rating again replaces the answer and keeps the questions not sent
    saved = student.put("/api/feedback", json={"ratings": {"easy": 2}}).get_json()["ratings"]
    assert saved == {"easy": 2, "overall": 5}
    assert student.get("/api/feedback").get_json()["ratings"] == saved


@pytest.mark.parametrize("ratings", [None, {}, {"easy": 0}, {"easy": 6}, {"easy": "5"}, {"easy": True},
                                     {"easy": 4.5}, {"nope": 3}, [("easy", 3)]])
def test_bad_ratings_are_refused(admin, ratings):
    response = login("jdelacruz01").put("/api/feedback", json={"ratings": ratings})
    assert response.status_code == 400 and response.get_json()["error"]


def test_admin_and_supervisor_do_not_rate(admin, supervisor):
    for client in (admin, supervisor):
        assert client.get("/api/feedback").status_code == 403
        assert client.put("/api/feedback", json={"ratings": {"easy": 5}}).status_code == 403


def test_only_the_admin_reads_the_totals(admin, teacher, supervisor):
    for client in (teacher, supervisor, login("jdelacruz01")):
        assert client.get("/api/feedback/summary").status_code == 403


def test_totals_average_and_counts_by_group(admin, teacher):
    login("jdelacruz01").put("/api/feedback", json={"ratings": {"easy": 5, "overall": 4}})
    other = next(user["username"] for user in admin.get("/api/users?role=student").get_json()["users"]
                 if user["username"] != "jdelacruz01")
    login(other).put("/api/feedback", json={"ratings": {"easy": 4}})
    teacher.put("/api/feedback", json={"ratings": {"easy": 3}})

    everyone = admin.get("/api/feedback/summary").get_json()
    assert everyone["respondents"] == 3
    easy = everyone["questions"][0]
    assert (easy["key"], easy["count"], easy["average"], easy["counts"]) == ("easy", 3, 4.0, [0, 0, 1, 1, 1])
    unrated = everyone["questions"][1]
    assert unrated["count"] == 0 and unrated["average"] is None and unrated["counts"] == [0] * 5

    students = admin.get("/api/feedback/summary?role=student").get_json()
    assert students["respondents"] == 2 and students["questions"][0]["average"] == 4.5
    teachers = admin.get("/api/feedback/summary?role=teacher").get_json()
    assert teachers["respondents"] == 1 and teachers["questions"][0]["average"] == 3.0
    assert admin.get("/api/feedback/summary?role=admin").status_code == 400


def test_the_totals_never_name_anyone(admin):
    login("jdelacruz01").put("/api/feedback", json={"ratings": {"easy": 5}})
    text = admin.get("/api/feedback/summary").get_data(as_text=True).lower()
    assert "jdelacruz01" not in text and "cruz" not in text


def test_rating_is_not_written_to_the_activity_log(admin, supervisor):
    login("jdelacruz01").put("/api/feedback", json={"ratings": {"easy": 5}})
    summaries = " ".join(entry["summary"] for entry in admin.get("/api/log?per_page=100").get_json()["entries"])
    assert "feedback" not in summaries.lower() and "rating" not in summaries.lower()


def test_feedback_page_per_role(admin, teacher, supervisor):
    assert 'id="feedback-form"' in login("jdelacruz01").get("/feedback").get_data(as_text=True)
    assert 'id="feedback-form"' in teacher.get("/feedback").get_data(as_text=True)
    assert 'id="feedback-results"' in admin.get("/feedback").get_data(as_text=True)
    assert supervisor.get("/feedback").headers["Location"].endswith("/dashboard")
