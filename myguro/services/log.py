from myguro.config import SCHOOL_TIMEZONE
from myguro.domain.log import CATEGORIES, LOG_ROLES, day_bounds
from myguro.domain.text import clean_name, like_pattern
from myguro.errors import ValidationError
from myguro.services.base import Service

DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100


class LogService(Service):
    """Reading the activity log (supervisors and the admin). Writing is Service.log."""

    @staticmethod
    def entry_json(row):
        return {
            "id": row["id"],
            "at": row["at"],  # UTC, "YYYY-MM-DD HH:MM:SS": the page shows it in the viewer's time
            "actor": {"id": row["actor_id"], "name": row["actor_name"], "username": row["actor_username"],
                      "role": row["actor_role"]},
            "action": row["action"],
            "category": row["category"],
            "summary": row["summary"],
            "target": {"type": row["target_type"], "id": row["target_id"], "name": row["target_name"]},
            "address": row["address"],
        }

    def list(self, query="", role="", category="", user_id=None, date_from="", date_to="", page=1,
             per_page=DEFAULT_PER_PAGE):
        """One page of entries, newest first, filtered by search text (person, target, summary), the
        person's role, category, one person (user_id) and a date range (school time, both days
        included). A page past the end shows the last page."""
        if role and role not in LOG_ROLES:
            raise ValidationError("Unknown role.")
        if category and category not in CATEGORIES:
            raise ValidationError("Unknown category.")
        filters = {"q": like_pattern(clean_name(query)) if clean_name(query) else None, "role": role,
                   "category": category, "user_id": user_id}
        if date_from:
            filters["date_from"] = day_bounds(date_from, SCHOOL_TIMEZONE)[0]
        if date_to:
            filters["date_to"] = day_bounds(date_to, SCHOOL_TIMEZONE)[1]
        per_page = max(1, min(per_page, MAX_PER_PAGE))
        total = self.logs.count(filters)
        pages = max(1, -(-total // per_page))  # rounded up
        page = max(1, min(page, pages))
        rows = self.logs.search(filters, per_page, (page - 1) * per_page)
        return {"entries": [self.entry_json(row) for row in rows], "page": page, "pages": pages,
                "per_page": per_page, "total": total}
