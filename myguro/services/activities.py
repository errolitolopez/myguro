from myguro.domain.docx_import import sections_from_lines
from myguro.domain.sheets import MAX_TITLE_LENGTH, clean_max_attempts, clean_sections, clean_title_subject
from myguro.errors import NotFoundError, ValidationError
from myguro.services.base import Service


class ActivityService(Service):
    """A teacher's learning activity sheets: sections (text or activity) and questions."""

    def require(self, activity_id):
        """The teacher's sheet, or NotFoundError."""
        row = self.activities.get_for_teacher(activity_id, self.user["id"])
        if row is None:
            raise NotFoundError("Activity not found.")
        return row

    def exists(self, activity_id):
        return self.activities.get_for_teacher(activity_id, self.user["id"]) is not None

    def activity_json(self, row):
        return {
            "id": row["id"],
            "title": row["title"],
            "subject": row["subject"],
            "max_attempts": row["max_attempts"],  # None = unlimited
            # True once a student submitted it: then it can't be edited
            "locked": self.activities.has_submissions(row["id"]),
            "deleted_at": row["deleted_at"],  # set while the sheet is deleted (archived)
            # How many classes or groups it is given to (0 = a draft), and how many are not started, open, closed
            "assigned": self.activities.count_assigned(row["id"]),
            "statuses": self.activities.count_by_status(row["id"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def list(self, deleted=False):
        """The teacher's sheets, or with deleted=True the ones they deleted (archived)."""
        return [{**self.activity_json(row), "sections": row["sections"], "questions": row["questions"]}
                for row in self.activities.list_for_teacher(self.user["id"], deleted)]

    def create(self, data):
        """Start a sheet (a draft) with its title and subject; sections come in the editor."""
        activity_id = self.activities.create(self.user["id"], *clean_title_subject(data))
        created = self.require(activity_id)
        self.log_activity("activity.created", f"Created the activity {created['title']}.", created)
        self.commit()
        return self.activity_json(created)

    def log_activity(self, action, summary, row):
        """An activity log entry about one sheet (row: the sheet, with id and title)."""
        self.log(action, "activities", summary, ("activity", row["id"], row["title"]))

    def import_docx_sheet(self, lines, data, dry_run):
        """Make a new draft sheet from the lines of a Word file (see domain/docx_import.py), with the
        title and subject in data. All or nothing: with any bad item nothing is created and every
        problem is listed with its section and item (where). dry_run only checks.

        Returns {imported, activity (after a real import), sections [{kind, title, questions, points}], errors}."""
        sections, errors = sections_from_lines(lines)
        return self.finish_import(sections, errors, data, dry_run)

    def finish_import(self, sections, errors, data, dry_run):
        title, subject = clean_title_subject(data)
        if errors:
            return {"imported": False, "activity": None, "sections": [], "errors": errors}
        preview = [{"kind": section.kind, "title": section.title or section.description[:60],
                    "questions": len(section.questions),
                    "points": sum(question.points for question in section.questions)} for section in sections]
        if dry_run:
            return {"imported": False, "activity": None, "sections": preview, "errors": []}
        activity_id = self.activities.create(self.user["id"], title, subject)
        self.activities.save_sections(activity_id, sections)
        self.log_activity("activity.imported", f"Imported the activity {title} from a file.", self.require(activity_id))
        self.commit()
        return {"imported": True, "activity": self.activity_json(self.require(activity_id)),
                "sections": preview, "errors": []}

    def get(self, activity_id):
        return {**self.activity_json(self.require(activity_id)), "sections": self.activities.sections(activity_id)}

    def save(self, activity_id, data):
        """Save the title, subject, and the sections with their questions, in the posted order."""
        self.require(activity_id)
        title, subject = clean_title_subject(data)
        sections = clean_sections(data.get("sections", []))
        if self.activities.has_submissions(activity_id):
            raise ValidationError("A student already submitted this activity, so it can't be changed "
                                  "anymore (their scores must stay fair).")
        self.activities.update_title(activity_id, title, subject)
        self.activities.save_sections(activity_id, sections)
        self.log_activity("activity.saved", f"Saved the activity {title}.", self.require(activity_id))
        self.commit()
        return self.get(activity_id)

    def duplicate(self, activity_id):
        """Copy a sheet (even a locked one) into a new draft named "<title> (copy)": same
        sections, questions and submissions allowed, none of the assignments or answers."""
        source = self.require(activity_id)
        suffix = " (copy)"
        title = source["title"][:MAX_TITLE_LENGTH - len(suffix)] + suffix
        new_id = self.activities.copy(activity_id, title)
        self.log_activity("activity.copied", f"Copied {source['title']} as {title}.", self.require(new_id))
        self.commit()
        return self.activity_json(self.require(new_id))

    def delete(self, activity_id):
        """Delete a sheet. One nobody has been given is really deleted; an assigned one is archived:
        hidden from the teacher's list and from students, with every assignment and answer kept so
        it can be restored. Returns True when it was archived."""
        row = self.require(activity_id)
        archived = bool(self.activities.count_assigned(activity_id))
        if archived:
            self.activities.archive(activity_id)
            self.assignments.reset_all(activity_id)  # not started again, so restoring it does not reopen it by itself
        else:
            self.activities.delete(activity_id)
        self.log_activity("activity.deleted", f"Deleted the activity {row['title']}"
                          + (" (archived: students lose access, their work is kept)." if archived else "."), row)
        self.commit()
        return archived

    def restore(self, activity_id):
        """Bring a deleted sheet back with its assignments (not started) and student work."""
        row = self.activities.get_for_teacher(activity_id, self.user["id"], include_deleted=True)
        if row is None or row["deleted_at"] is None:
            raise NotFoundError("Activity not found.")
        self.activities.restore(activity_id)
        self.log_activity("activity.restored", f"Restored the activity {row['title']} (its assignments are not started).", row)
        self.commit()
        return self.activity_json(self.require(activity_id))

    def update_settings(self, activity_id, data):
        """Settings that may change anytime, even after students submitted: max_attempts
        (1 to 10, or None = unlimited), and title with subject (they don't affect any score)."""
        before = self.require(activity_id)
        if "max_attempts" in data:
            self.activities.set_max_attempts(activity_id, clean_max_attempts(data.get("max_attempts")))
        if "title" in data or "subject" in data:
            self.activities.update_title(activity_id, *clean_title_subject(data))
        row = self.require(activity_id)
        if row["max_attempts"] != before["max_attempts"]:
            allowed = row["max_attempts"] or "unlimited"
            self.log_activity("activity.attempts_changed", f"Changed submissions allowed of {row['title']} to {allowed}.", row)
        if (row["title"], row["subject"]) != (before["title"], before["subject"]):
            self.log_activity("activity.saved", f"Renamed the activity {before['title']} to {row['title']}.", row)
        self.commit()
        return self.activity_json(row)
