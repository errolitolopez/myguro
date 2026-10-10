"""How things are sent to the browser (the JSON shapes the pages expect)."""


def user_json(row):
    return {
        "id": row["id"],
        "name": row["name"],  # "Last, First M."
        "last_name": row["last_name"],
        "first_name": row["first_name"],
        "middle_initial": row["middle_initial"],
        "username": row["username"],
        "active": bool(row["active"]),
        "activated": bool(row["activated"]),
        "must_change_password": bool(row["must_change_password"]),
        "created_at": row["created_at"],
        "grade": row["grade"],
        "section": row["section"],
    }


def class_json(row):
    return {"id": row["id"], "name": row["name"], "subject": row["subject"]}


def class_title(name, subject):
    """"Grade 9 - Rizal · Science" (just the name when there's no subject)."""
    return name + (f" · {subject}" if subject else "")
