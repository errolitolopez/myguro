"""Checking a student's saved answers when an attempt is submitted (by the student or by a close)."""

from myguro.domain.grading import check_answer


def grade_attempt(service, assignment_id, submission, questions, student_id):
    """Check every question of the attempt against the student's saved answers and store the result.
    service is any Service (it gives the repositories). Does not mark the attempt submitted."""
    answers = service.submissions.answers(submission["id"])
    # Short answers the teacher already scored in the previous attempt keep their score when
    # the student didn't change them, so the teacher doesn't check the same text twice.
    previous = service.submissions.latest(assignment_id, student_id, submitted_only=True)
    earlier_scores = service.submissions.scored_answers(previous["id"]) if previous else {}
    for question in questions:
        is_correct, points = check_answer(question, answers.get(question["id"]))
        earlier = earlier_scores.get(question["id"])
        if (question["type"] == "short_answer" and earlier and question["id"] in answers
                and earlier[0] == answers[question["id"]]):
            points = earlier[1]
            is_correct = points == question["points"]
        # Unanswered questions get an empty answer, so they show as 0 points (short answers too).
        answered = question["id"] in answers
        service.submissions.set_check(submission["id"], question["id"],
                                      is_correct if answered else False, points if answered else 0, answered)
