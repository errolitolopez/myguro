"""The timetable generator: its hard rules, its preferences, and the checker for swaps."""

import time

from myguro.domain.schedule import DAYS, check, generate

PERIODS = 6


def small_case():
    """Three sections sharing four teachers, in the shape of a real class program."""
    subjects = [("MATH", 1, 5), ("SCI", 2, 5), ("ENG", 3, 4), ("PE", 4, 2), ("HOME", 1, 1)]
    assignments = [{"section_id": s, "subject": name, "teacher_id": teacher, "per_week": count}
                   for s in (1, 2, 3) for name, teacher, count in subjects]
    return assignments, {teacher: {} for teacher in (1, 2, 3, 4)}


def test_every_assignment_gets_exactly_its_periods_with_no_clashes():
    assignments, teachers = small_case()
    result = generate(assignments, teachers, PERIODS, seed=1, restarts=2, steps=8000)
    assert result["unplaced"] == [] and result["problems"] == []
    assert check(result["slots"], assignments, teachers, PERIODS) == []
    assert len(result["slots"]) == sum(item["per_week"] for item in assignments)


def test_the_same_seed_gives_the_same_timetable():
    assignments, teachers = small_case()
    assert generate(assignments, teachers, PERIODS, seed=3)["slots"] == generate(assignments, teachers, PERIODS, seed=3)["slots"]


def test_a_blocked_period_is_never_used():
    assignments, teachers = small_case()
    teachers[2]["blocked"] = {(day, 0) for day in range(DAYS)}  # teacher 2 cannot teach the first period
    result = generate(assignments, teachers, PERIODS, seed=1)
    assert result["unplaced"] == []
    assert not [slot for slot in result["slots"] if slot[4] == 2 and slot[2] == 0]


def test_an_impossible_load_is_reported_and_the_rest_is_still_built():
    assignments, teachers = small_case()
    assignments.append({"section_id": 4, "subject": "ART", "teacher_id": 4, "per_week": 29})  # teacher 4 is full
    result = generate(assignments, teachers, PERIODS, seed=1, restarts=2, steps=2000)
    assert any(problem["kind"] == "teacher_full" for problem in result["problems"])
    assert result["unplaced"]  # something could not be placed, and the answer says so


def test_teachers_have_no_long_gaps_and_sections_no_holes():
    assignments, teachers = small_case()
    result = generate(assignments, teachers, PERIODS, rules={"max_gap": 1}, seed=2)
    problems = check(result["slots"], assignments, teachers, PERIODS, {"max_gap": 1})
    assert [p for p in problems if p["kind"] in ("long_gap", "hole", "teacher_double")] == []


def test_a_subject_is_at_most_twice_a_day_and_spread_over_the_week():
    assignments, teachers = small_case()
    result = generate(assignments, teachers, PERIODS, seed=1)
    days = {}
    for section, day, period, subject, teacher in result["slots"]:
        days.setdefault((section, subject), []).append(day)
    for (section, subject), used in days.items():
        assert max(used.count(day) for day in set(used)) <= 2
    assert len(set(days[(1, "MATH")])) == 5  # five periods a week: one every day


def test_the_checker_names_what_a_hand_swap_breaks():
    assignments, teachers = small_case()
    slots = generate(assignments, teachers, PERIODS, seed=1)["slots"]
    first = next(slot for slot in slots if slot[0] == 1)
    other_section = next(slot for slot in slots if slot[0] == 2 and slot[4] == first[4] and slot[1:3] != first[1:3])
    # Move the other section's class of the same teacher into the first one's period: a double booking
    moved = [slot for slot in slots if slot != other_section] + [(2, first[1], first[2], other_section[3], other_section[4])]
    assert any(problem["kind"] == "teacher_double" for problem in check(moved, assignments, teachers, PERIODS))
    teachers[first[4]]["blocked"] = {(first[1], first[2])}
    assert any(problem["kind"] == "teacher_blocked" for problem in check(slots, assignments, teachers, PERIODS))


def test_a_ten_section_school_is_built_in_a_few_seconds():
    """The size of the real Grade 12 program: 10 sections, 8 subjects each, teachers shared by many sections."""
    subjects = [("PHILO", 4), ("CPAR", 4), ("ENTREP", 4), ("PR2", 4), ("PE3", 2), ("HRGP", 1), ("TRENDS", 5), ("CESC", 5)]
    assignments = []
    for section in range(1, 11):
        for index, (name, count) in enumerate(subjects):
            # ten sections share two teachers per subject
            assignments.append({"section_id": section, "subject": name,
                                "teacher_id": index * 2 + (section % 2), "per_week": count})
    teachers = {item["teacher_id"]: {} for item in assignments}
    started = time.time()
    result = generate(assignments, teachers, PERIODS, seed=1, restarts=4, steps=20000)
    assert result["unplaced"] == []
    # Every period given, nobody in two places (the gaps and holes are preferences, not guarantees)
    hard = {"teacher_double", "teacher_blocked", "wrong_count"}
    assert [p for p in check(result["slots"], assignments, teachers, PERIODS) if p["kind"] in hard] == []
    assert time.time() - started < 60
