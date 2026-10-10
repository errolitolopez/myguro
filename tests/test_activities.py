"""Teacher: activity sheets with text and activity sections and questions."""

import pytest

from conftest import SAMPLE_SECTIONS, error, login, make_activity


def test_create_save_and_reload(teacher):
    activity_id, questions = make_activity(teacher)
    activity = teacher.get(f"/api/activities/{activity_id}").get_json()["activity"]
    assert [section["kind"] for section in activity["sections"]] == ["text", "activity", "activity"]
    assert activity["sections"][0]["description"] == "Early Eastern\nBeginnings"
    pretest = activity["sections"][1]["questions"]
    assert [q["type"] for q in pretest] == ["multiple_choice", "true_false", "identification", "fill_blank"]
    assert pretest[2]["answer"] == ["Taoism", "Daoism"]
    assert activity["max_attempts"] == 1 and activity["assigned"] == 0 and activity["locked"] is False
    listed = teacher.get("/api/activities").get_json()["activities"][0]
    assert (listed["sections"], listed["questions"]) == (3, 5)


def test_ids_stay_when_saving_again(teacher):
    activity_id, questions = make_activity(teacher)
    sections = teacher.get(f"/api/activities/{activity_id}").get_json()["activity"]["sections"]
    sections.reverse()
    sections[0]["questions"].append(sections[1]["questions"].pop(0))  # move a question to another section
    response = teacher.put(f"/api/activities/{activity_id}", json={"title": "T", "sections": sections})
    saved = response.get_json()["activity"]["sections"]
    assert sorted(q["id"] for s in saved for q in s["questions"]) == sorted(questions)


@pytest.mark.parametrize("question, message", [
    ({"type": "essay", "prompt": "x", "answer": 1}, "unknown question type"),
    ({"type": "multiple_choice", "prompt": " ", "choices": ["a", "b"], "answer": 0}, "type the question"),
    ({"type": "multiple_choice", "prompt": "Q", "choices": ["a"], "answer": 0}, "give 2 to 6 choices"),
    ({"type": "multiple_choice", "prompt": "Q", "choices": ["a", ""], "answer": 0}, "a choice is empty"),
    ({"type": "multiple_choice", "prompt": "Q", "choices": ["a", "b"], "answer": None}, "choose the correct answer"),
    ({"type": "true_false", "prompt": "Q", "answer": "false"}, "choose True or False"),
    ({"type": "identification", "prompt": "Q", "answer": [" "]}, "type the correct answer"),
    ({"type": "fill_blank", "prompt": "No blank", "answer": []}, "put ___"),
    ({"type": "fill_blank", "prompt": "A ___ b ___", "answer": [["x"]]}, "type the answer for each blank"),
    ({"type": "short_answer", "prompt": "Q", "answer": "", "points": 0}, "points must be a whole number"),
])
def test_question_rules(teacher, question, message):
    activity_id, _ = make_activity(teacher)
    response = teacher.put(f"/api/activities/{activity_id}",
                           json={"title": "T", "sections": [{"kind": "activity", "title": "A", "questions": [question]}]})
    assert response.status_code == 400 and message in error(response)


def test_section_rules(teacher):
    activity_id, _ = make_activity(teacher)
    put = lambda sections: error(teacher.put(f"/api/activities/{activity_id}", json={"title": "T", "sections": sections}))
    assert put([{"kind": "text"}]) == "Section 1 is empty. Type a title or description, or delete it."
    assert put([{"kind": "activity", "title": "A", "questions": []}]).startswith("Section 1 is an activity with no")
    assert put([{"kind": "quiz", "title": "A"}]) == "Section 1: unknown kind of section."
    assert error(teacher.put(f"/api/activities/{activity_id}", json={"title": " ", "sections": []})) == \
        "Title is required."


def test_activities_are_private(teacher, other_teacher):
    activity_id, _ = make_activity(teacher)
    assert other_teacher.get(f"/api/activities/{activity_id}").status_code == 404
    assert other_teacher.put(f"/api/activities/{activity_id}", json={"title": "x", "sections": []}).status_code == 404
    assert other_teacher.delete(f"/api/activities/{activity_id}").status_code == 404
    assert login("jdelacruz01").get(f"/api/activities/{activity_id}").status_code == 403


def test_delete_draft(teacher):
    activity_id, _ = make_activity(teacher)
    assert teacher.delete(f"/api/activities/{activity_id}").status_code == 200
    assert teacher.get(f"/api/activities/{activity_id}").status_code == 404


def test_settings_max_attempts(teacher):
    activity_id, _ = make_activity(teacher)
    put = lambda value: teacher.put(f"/api/activities/{activity_id}/settings", json={"max_attempts": value})
    assert put(3).get_json()["activity"]["max_attempts"] == 3
    assert put(None).get_json()["activity"]["max_attempts"] is None
    for bad in (0, 11, "2", True):
        assert put(bad).status_code == 400


def test_sections_must_have_content_before_assigning(teacher):
    activity_id = teacher.post("/api/activities", json={"title": "Empty"}).get_json()["activity"]["id"]
    class_id = teacher.post("/api/classes", json={"name": "C"}).get_json()["class"]["id"]
    response = teacher.put(f"/api/activities/{activity_id}/assignments", json={"assignments": [{"class_id": class_id}]})
    assert error(response) == "Add at least one section before giving this activity to a class."


SAMPLE = SAMPLE_SECTIONS  # re-exported for other tests


def test_formatted_description_is_cleaned_and_kept(teacher):
    activity_id, _ = make_activity(teacher)
    sections = teacher.get(f"/api/activities/{activity_id}").get_json()["activity"]["sections"]
    assert sections[0]["description_format"] == "plain"
    sections[0]["description_format"] = "rich"
    sections[0]["description"] = ('<p onclick="x()">Hi <b>there</b></p><script>alert(1)</script>'
                                  '<ul><li>one</li><li><a href="http://x">two</a></ul>')
    response = teacher.put(f"/api/activities/{activity_id}", json={"title": "T", "sections": sections})
    assert response.status_code == 200, response.get_json()
    saved = teacher.get(f"/api/activities/{activity_id}").get_json()["activity"]["sections"][0]
    assert saved["description_format"] == "rich"
    assert saved["description"] == "<p>Hi <b>there</b></p><ul><li>one</li><li>two</li></ul>"


def test_formatted_description_with_no_text_is_empty(teacher):
    activity_id, _ = make_activity(teacher)
    sections = teacher.get(f"/api/activities/{activity_id}").get_json()["activity"]["sections"]
    sections[0].update(description_format="rich", description="<div><br></div>", title="")
    response = teacher.put(f"/api/activities/{activity_id}", json={"title": "T", "sections": sections})
    assert response.status_code == 400
    sections[0]["description_format"] = "fancy"
    assert teacher.put(f"/api/activities/{activity_id}", json={"title": "T", "sections": sections}).status_code == 400
