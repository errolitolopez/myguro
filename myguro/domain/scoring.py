"""Adding up points."""


def empty_score():
    return {"earned": 0, "possible": 0, "pending": 0}


def summarize(rows):
    """Points per section and in total from rows of (section_id, possible, earned, type).
    pending = short answers the teacher hasn't scored yet."""
    sections = {}
    total = empty_score()
    for row in rows:
        part = sections.setdefault(row["section_id"], empty_score())
        pending = row["type"] == "short_answer" and row["earned"] is None
        for bucket in (part, total):
            bucket["possible"] += row["possible"]
            if pending:
                bucket["pending"] += row["possible"]
            else:
                bucket["earned"] += row["earned"] or 0
    return {"total": total, "sections": sections, "paper": False}


def paper_summary(paper_score, possible):
    """A paper score: the total only."""
    return {"total": {"earned": paper_score, "possible": possible, "pending": 0}, "sections": {}, "paper": True}


def average_percent(scores):
    """Average of what's checked so far, as a percent (None when nothing is checked)."""
    checked = sum(score["possible"] - score["pending"] for score in scores)
    if not scores or not checked:
        return None
    return round(100 * sum(score["earned"] for score in scores) / checked)
