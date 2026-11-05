"""Check with AI: off by default, a suggestion for a short answer only, never changes a score by itself."""

import pytest

from conftest import assign, error, login, make_activity, make_class


@pytest.fixture(autouse=True)
def no_real_key(app, tmp_path, monkeypatch):
    """Never use the real key saved in instance/gemini.env: a test must not call the real service."""
    monkeypatch.setattr(app, "instance_path", str(tmp_path))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


@pytest.fixture
def submitted(teacher):
    """(submission id, short answer question id, multiple choice question id, results page of that student)."""
    class_id, students = make_class(teacher)
    activity_id, q = make_activity(teacher)
    assignment_id = assign(teacher, activity_id, class_id)
    student = login(students[0]["username"])
    student.post(f"/api/my-activities/{assignment_id}/submit",
                 json={"answers": {str(q[0]): 1, str(q[4]): "Because it teaches balance."}})
    detail = teacher.get(f"/api/assignments/{assignment_id}/students/{students[0]['id']}").get_json()["detail"]
    return detail["id"], q[4], q[0], f"/results/{assignment_id}/students/{students[0]['id']}"


def url(submission_id, question_id):
    return f"/api/submissions/{submission_id}/questions/{question_id}/ai-check"


def test_off_by_default_then_the_admin_turns_it_on(admin, teacher, submitted):
    submission_id, short_id, _, _ = submitted
    assert admin.get("/api/settings").get_json()["settings"]["ai_check_enabled"] is False
    assert teacher.post(url(submission_id, short_id)).status_code == 404  # looks like it does not exist
    assert teacher.put("/api/settings", json={"ai_check_enabled": True}).status_code == 403
    assert error(admin.put("/api/settings", json={"ai_check_enabled": "yes"})) == "Choose on or off."
    assert admin.put("/api/settings", json={"ai_check_enabled": True}).get_json()["settings"]["ai_check_enabled"]


def test_suggestion_is_clamped_and_changes_no_score(admin, teacher, submitted, monkeypatch):
    submission_id, short_id, _, _ = submitted
    admin.put("/api/settings", json={"ai_check_enabled": True})
    sent = []
    monkeypatch.setattr("myguro.ai_check_client.ask_model",
                        lambda text: sent.append(text) or {"points": 99, "explanation": "Names the idea. Missing an example."})
    data = teacher.post(url(submission_id, short_id)).get_json()
    assert data == {"points": 5, "explanation": "Names the idea. Missing an example.", "max_points": 5}  # 99 -> max 5
    # what was sent: the question, the guide, the points and the answer, and no names
    assert "Why?" in sent[0] and "key points" in sent[0] and "Maximum points: 5" in sent[0]
    assert "<answer>\nBecause it teaches balance.\n</answer>" in sent[0]
    assert "Cruz" not in sent[0] and "jdelacruz" not in sent[0]
    # nothing was scored: the short answer is still waiting for the teacher
    entries = admin.get("/api/log?category=checking").get_json()["entries"]
    assert any(entry["action"] == "checking.ai_check" and "Because" not in entry["summary"] for entry in entries)


def test_only_a_submitted_short_answer_of_your_own_student_can_be_checked(admin, teacher, other_teacher, submitted,
                                                                         monkeypatch):
    submission_id, short_id, choice_id, _ = submitted
    admin.put("/api/settings", json={"ai_check_enabled": True})
    monkeypatch.setattr("myguro.ai_check_client.ask_model", lambda text: {"points": 3, "explanation": "ok"})
    assert error(teacher.post(url(submission_id, choice_id))) == "Question not found."  # not a short answer
    assert other_teacher.post(url(submission_id, short_id)).status_code == 404
    assert teacher.post(url(99999, short_id)).status_code == 404


def test_unusable_reply_and_daily_limit(admin, teacher, submitted, monkeypatch):
    submission_id, short_id, _, _ = submitted
    admin.put("/api/settings", json={"ai_check_enabled": True})
    # no key, no network: the reply is None, so the teacher is told it is not available
    assert error(teacher.post(url(submission_id, short_id))) == "The AI check is not available right now."
    monkeypatch.setattr("myguro.ai_check_client.ask_model", lambda text: {"points": "lots", "explanation": ""})
    assert teacher.post(url(submission_id, short_id)).status_code == 400
    # the limit counts every call, even a failing one
    monkeypatch.setattr("myguro.domain.ai_check.MAX_PER_DAY", 2)
    assert error(teacher.post(url(submission_id, short_id))) == "You reached today's limit. Try again tomorrow."


def test_the_button_is_on_the_checking_page_only_while_it_is_on(admin, teacher, submitted):
    page = submitted[3]
    assert 'data-ai-check="0"' in teacher.get(page).get_data(as_text=True)
    admin.put("/api/settings", json={"ai_check_enabled": True})
    assert 'data-ai-check="1"' in teacher.get(page).get_data(as_text=True)
