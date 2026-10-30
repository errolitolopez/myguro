"""Teacher: print an activity sheet as a PDF (student copy and answer key)."""

from conftest import make_activity


def test_print_student_copy_and_answer_key(teacher, other_teacher):
    activity_id, _ = make_activity(teacher)
    student_copy = teacher.get(f"/activities/{activity_id}/print.pdf")
    assert student_copy.status_code == 200 and student_copy.mimetype == "application/pdf"
    assert student_copy.data.startswith(b"%PDF")
    answer_key = teacher.get(f"/activities/{activity_id}/print.pdf?key=1")
    assert answer_key.status_code == 200 and answer_key.data.startswith(b"%PDF")
    assert answer_key.data != student_copy.data  # the key adds the answers


def test_print_is_only_for_the_owner(teacher, other_teacher):
    activity_id, _ = make_activity(teacher)
    response = other_teacher.get(f"/activities/{activity_id}/print.pdf")
    assert response.status_code == 302 and "/activities" in response.headers["Location"]


def test_the_sheet_is_printed_in_a_times_style_font(teacher):
    # Liberation Serif has the same letter widths as Times New Roman; the sheet is compact to save paper.
    activity_id, _ = make_activity(teacher)
    data = teacher.get(f"/activities/{activity_id}/print.pdf").data
    assert b"LiberationSerif" in data and b"DejaVu" not in data

