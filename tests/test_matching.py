"""Matching type: Column A items matched to Column B choices, part credit per item."""

import json

import pytest

from conftest import assign, error, login, make_activity, make_class

MATCHING = {"type": "matching", "prompt": "Match the tradition with its country.",
            "choices": ["India", "China", "Japan", "Greece"],
            "answer": [{"item": "Hinduism", "match": 0}, {"item": "Taoism", "match": 1},
                       {"item": "Shinto", "match": 2}, {"item": "Stoicism", "match": 3}],
            "points": 8}
SECTIONS = [{"kind": "activity", "title": "Match", "questions": [MATCHING]}]


def setup(teacher):
    class_id, students = make_class(teacher)
    activity_id, questions = make_activity(teacher, sections=SECTIONS)
    assignment_id = assign(teacher, activity_id, class_id)
    teacher.put(f"/api/assignments/{assignment_id}/release", json={"released": True})
    return assignment_id, activity_id, questions[0], students


def test_save_and_reload(teacher):
    activity_id, _ = make_activity(teacher, sections=SECTIONS)
    question = teacher.get(f"/api/activities/{activity_id}").get_json()["activity"]["sections"][0]["questions"][0]
    assert question["type"] == "matching" and question["choices"] == MATCHING["choices"]
    assert question["answer"] == MATCHING["answer"]


@pytest.mark.parametrize("change, message", [
    ({"choices": ["only one"]}, "give 2 to 12 choices"),
    ({"choices": ["a", ""]}, "a choice is empty"),
    ({"answer": [{"item": "x", "match": 0}]}, "give 2 to 10 items"),
    ({"answer": [{"item": "x", "match": 0}, {"item": " ", "match": 1}]}, "item 2 is empty"),
    ({"answer": [{"item": "x", "match": 0}, {"item": "y", "match": None}]}, "choose the match of item 2"),
    ({"answer": [{"item": "x", "match": 0}, {"item": "y", "match": 9}]}, "choose the match of item 2"),
    ({"answer": "India"}, "items are not valid"),
])
def test_rules(teacher, change, message):
    activity_id, _ = make_activity(teacher, sections=SECTIONS)
    question = {**MATCHING, **change}
    response = teacher.put(f"/api/activities/{activity_id}", json={"title": "T", "subject": "Philosophy", "sections": [
        {"kind": "activity", "title": "A", "questions": [question]}]})
    assert response.status_code == 400 and message in error(response)


def test_student_sheet_has_items_but_no_key(teacher):
    assignment_id, _, _, students = setup(teacher)
    sheet = login(students[0]["username"]).get(f"/api/my-activities/{assignment_id}").get_json()["activity"]
    question = sheet["sections"][0]["questions"][0]
    assert question["items"] == ["Hinduism", "Taoism", "Shinto", "Stoicism"]
    assert question["choices"] == MATCHING["choices"]
    assert '"answer"' not in json.dumps(sheet) and '"match"' not in json.dumps(sheet)


def test_answers_are_checked(teacher):
    assignment_id, _, question_id, students = setup(teacher)
    student = login(students[0]["username"])
    put = lambda value: student.put(f"/api/my-activities/{assignment_id}/answers",
                                    json={"answers": {str(question_id): value}})
    assert error(put([0, 1])) == "An answer is not valid."  # wrong length
    assert error(put([0, 1, 2, 9])) == "An answer is not valid."  # no such choice
    assert error(put([0, 1, 2, "3"])) == "An answer is not valid."
    assert put([0, None, None, None]).status_code == 200  # partly answered is saved
    response = student.post(f"/api/my-activities/{assignment_id}/submit",
                            json={"answers": {str(question_id): [0, 1, 3, None]}})
    # 2 of 4 right: 8 * 2 // 4 = 4 of 8
    assert response.get_json()["activity"]["score"]["total"] == {"earned": 4, "pending": 0, "possible": 8}


def test_teacher_sees_picks_and_key(teacher):
    assignment_id, _, question_id, students = setup(teacher)
    student = login(students[0]["username"])
    student.post(f"/api/my-activities/{assignment_id}/submit",
                 json={"answers": {str(question_id): [0, None, 2, 0]}})
    detail = teacher.get(f"/api/assignments/{assignment_id}/students/{students[0]['id']}").get_json()["detail"]
    question = detail["sections"][0]["questions"][0]
    assert question["given"] == [0, None, 2, 0]
    assert [pair["match"] for pair in question["answer"]] == [0, 1, 2, 3]
    assert (question["earned"], question["is_correct"]) == (4, False)
