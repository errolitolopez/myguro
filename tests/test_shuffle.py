"""Shuffled questions and choices (beta, a setting of each teacher): a different order for each student, stable on
every visit, answers still stored and graded in the teacher's own order."""

from conftest import assign, error, login, make_activity, make_class


def turn_on(teacher, **settings):
    return teacher.put("/api/teacher-settings", json=settings)


def setup(teacher):
    class_id, students = make_class(teacher)
    activity_id, q = make_activity(teacher)
    return assign(teacher, activity_id, class_id), q, students


def sheet(student, assignment_id):
    return student.get(f"/api/my-activities/{assignment_id}").get_json()["activity"]


def pretest(data):
    return data["sections"][1]["questions"]  # section 0 is the text part; section 1 the pre-test


def test_off_by_default_and_only_the_teacher_changes_it(teacher, admin):
    assert teacher.get("/api/teacher-settings").get_json()["settings"] == \
        {"shuffle_questions": False, "shuffle_choices": False}
    assert error(turn_on(teacher, shuffle_choices="yes")) == "Choose on or off."
    assert turn_on(teacher, shuffle_choices=True).get_json()["settings"]["shuffle_choices"] is True
    assert teacher.get("/api/teacher-settings").get_json()["settings"]["shuffle_questions"] is False
    assert admin.get("/api/teacher-settings").status_code == 403
    assert login("jdelacruz01").get("/api/teacher-settings").status_code == 403


def test_the_setting_belongs_to_one_teacher(teacher, other_teacher):
    turn_on(teacher, shuffle_questions=True)
    assert other_teacher.get("/api/teacher-settings").get_json()["settings"]["shuffle_questions"] is False


def test_nothing_changes_while_it_is_off(teacher):
    assignment_id, q, students = setup(teacher)
    for student in students:
        questions = pretest(sheet(login(student["username"]), assignment_id))
        assert [question["id"] for question in questions] == q[:4]
        assert questions[0]["choices"] == ["Confucianism", "Hinduism", "Taoism"]


def test_questions_get_their_own_order_that_stays_the_same(teacher):
    assignment_id, q, students = setup(teacher)
    turn_on(teacher, shuffle_questions=True)
    orders = set()
    for student in students:
        client = login(student["username"])
        ids = [question["id"] for question in pretest(sheet(client, assignment_id))]
        assert sorted(ids) == sorted(q[:4])  # the same questions, only in another order
        assert ids == [question["id"] for question in pretest(sheet(client, assignment_id))]  # same every visit
        orders.add(tuple(ids))
    assert len(orders) > 1  # six students do not all get one order


def test_shuffled_choices_are_still_stored_and_graded_in_the_teachers_order(teacher):
    assignment_id, q, students = setup(teacher)
    turn_on(teacher, shuffle_choices=True)
    student = login(students[0]["username"])
    choices = pretest(sheet(student, assignment_id))[0]["choices"]
    assert sorted(choices) == ["Confucianism", "Hinduism", "Taoism"]
    # the student taps "Hinduism" wherever it is on their screen, and the answer is saved as the teacher's choice B
    shown = choices.index("Hinduism")
    student.put(f"/api/my-activities/{assignment_id}/answers", json={"answers": {str(q[0]): shown}})
    assert sheet(student, assignment_id)["answers"][str(q[0])] == shown  # they see their own tap again
    data = student.post(f"/api/my-activities/{assignment_id}/submit", json={"answers": {str(q[0]): shown}}).get_json()["activity"]
    assert data["sections"][1]["questions"][0]["choices"] == choices
    detail = teacher.get(f"/api/assignments/{assignment_id}/students/{students[0]['id']}").get_json()["detail"]
    first = detail["sections"][1]["questions"][0]
    assert first["given"] == 1 and first["is_correct"] is True and first["earned"] == 1  # Hinduism is B


def test_a_try_again_is_shuffled_again_and_keeps_the_choice(teacher):
    assignment_id, q, students = setup(teacher)
    turn_on(teacher, shuffle_choices=True)
    teacher.put(f"/api/activities/{teacher.get('/api/activities').get_json()['activities'][0]['id']}/settings",
                json={"max_attempts": 3})
    student = login(students[0]["username"])
    shown = pretest(sheet(student, assignment_id))[0]["choices"].index("Taoism")
    student.post(f"/api/my-activities/{assignment_id}/submit", json={"answers": {str(q[0]): shown}})
    again = student.post(f"/api/my-activities/{assignment_id}/retry").get_json()["activity"]
    question = pretest(again)[0]
    # whatever the new order is, the screen shows the answer they gave before
    assert question["choices"][again["answers"][str(q[0])]] == "Taoism"


def test_the_teacher_turning_it_on_changes_the_order_not_the_saved_answers(teacher):
    assignment_id, q, students = setup(teacher)
    student = login(students[0]["username"])
    student.put(f"/api/my-activities/{assignment_id}/answers", json={"answers": {str(q[0]): 1}})  # Hinduism
    turn_on(teacher, shuffle_choices=True)
    question = pretest(sheet(student, assignment_id))[0]
    assert question["choices"][sheet(student, assignment_id)["answers"][str(q[0])]] == "Hinduism"
