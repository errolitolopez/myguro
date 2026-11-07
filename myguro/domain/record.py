"""A student's record: their activities grouped by teacher and subject, with averages. No Flask, no SQL."""

from myguro.domain import scoring


def subject_key(subject):
    """subject_key("  Social   Studies ") -> "social studies" (two spellings of one subject stay together)."""
    return " ".join((subject or "").split()).lower()


def percent_of(score):
    """The percent of the points checked so far, or None when nothing is checked yet."""
    checked = score["possible"] - score["pending"]
    return round(100 * score["earned"] / checked) if checked else None


def build_record(activities):
    """The record from the student's activity list (StudentWorkService.list()).

    A score only counts once the teacher released it: the list already holds None for the others,
    so a hidden score can never reach the average or the page."""
    subjects = {}
    for item in activities:
        group = subjects.setdefault((item["teacher_id"], subject_key(item["subject"])), {
            "subject": " ".join((item["subject"] or "").split()),
            "teacher": item["teacher"], "teacher_id": item["teacher_id"], "activities": [], "scores": []})
        score = item["score"]
        group["activities"].append({
            "id": item["id"], "title": item["title"], "class_name": item["class_name"],
            "due_date": item["due_date"], "status": item["status"], "closed": item["closed"],
            "done": item["done"], "late": item["late"], "paper": item["paper"],
            "scores_released": item["scores_released"],
            "score": score, "percent": percent_of(score) if score else None,
        })
        if score:
            group["scores"].append(score)

    result, all_scores = [], []
    for group in subjects.values():
        all_scores += group["scores"]
        result.append({**{key: value for key, value in group.items() if key != "scores"},
                       "average": scoring.average_percent(group["scores"])})
    result.sort(key=lambda group: (group["subject"] == "", group["teacher"].lower(), group["subject"].lower()))
    return {
        "average": scoring.average_percent(all_scores),
        "given": len(activities),
        "done": sum(1 for item in activities if item["done"]),
        "late": sum(1 for item in activities if item["late"]),
        "subjects": result,
    }
