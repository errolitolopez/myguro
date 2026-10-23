from werkzeug.security import generate_password_hash

from myguro.domain.accounts import (
    ACCOUNT_ROLES, MAX_SECTION_LENGTH, check_new_account_password, clean_grade_section, clean_middle_initial,
    clean_person_name, clean_username, display_name, grade_from_text, make_temp_password, name_from_request,
    split_full_name, suggest_username,
)
from myguro.domain.text import clean_name, like_pattern, plural
from myguro.errors import NotFoundError, ValidationError
from myguro.services.base import Service
from myguro.services.presenters import user_json
from myguro.services.settings import SettingsService


DEFAULT_PER_PAGE = 20
MAX_BATCH = 1000
MAX_PER_PAGE = 100

# What the import sends back for each student
IMPORT_FIELDS = ("row", "name", "last_name", "first_name", "middle_initial", "username", "grade", "section")


class AccountService(Service):
    """The admin's work on teacher and student accounts (there is no sign-up)."""

    def account_json(self, row):
        """user_json plus the role and how many classes the teacher teaches or the student is in."""
        return {**user_json(row), "role": row["role"], "classes": self.users.count_classes(row)}

    @staticmethod
    def filters(query="", grade=None, name="", section="", status=None):
        """The search and the advanced filters (full name, grade, section, status) as the
        arguments the repository takes after the role: (pattern, grade, name_words, section_pattern,
        status).
        Every word typed in the full name must be in the name, in any order."""
        pattern = like_pattern(clean_name(query))
        name_words = tuple(like_pattern(word) for word in clean_name(name).replace(",", " ").split())
        section = clean_name(section)
        return pattern, grade, name_words, like_pattern(section) if section else None, status

    def list(self, role, query="", grade=None, page=1, per_page=DEFAULT_PER_PAGE, name="", section="",
             status=None):
        """One page of teachers or students, searched (name, username, section) and filtered by
        grade (None = all, "" = no grade), full name, section and status (active, pending, deactivated). A page past the end shows the
        last page."""
        if role not in ACCOUNT_ROLES:
            raise ValidationError("Unknown role.")
        per_page = max(1, min(per_page, MAX_PER_PAGE))
        search = self.filters(query, grade, name, section, status)
        total = self.users.count_matching(role, *search)
        pages = max(1, -(-total // per_page))  # rounded up
        page = max(1, min(page, pages))
        rows = self.users.search(role, *search, limit=per_page, offset=(page - 1) * per_page)
        return {
            "users": [self.account_json(row) for row in rows],
            "page": page,
            "pages": pages,
            "per_page": per_page,
            "total": total,  # matching the search / filter
            "all_count": self.users.count(role),
            "active_count": self.users.count(role, active_only=True),
        }

    def create(self, data):
        """Create a teacher or student. Returns (account, temporary password): the password is
        shown once so the admin can give it; they must change it on first login."""
        role = data.get("role", "teacher")
        if role not in ACCOUNT_ROLES:
            raise ValidationError("Unknown role.")
        names = name_from_request(data)
        grade, section = "", ""
        if role == "student":
            grade, section = self.grade_section(data)
        username = clean_username(data.get("username"))
        password = check_new_account_password(str(data.get("password", "")) or make_temp_password())
        if self.users.username_taken(username):
            raise ValidationError(f"The username \"{username}\" is already taken.")
        # A new student starts disabled: the admin enables the account first.
        user_id = self.users.create(names, username, generate_password_hash(password), role, grade, section,
                                    active=role != "student")
        created = self.users.get(user_id)
        self.log("account.created", "accounts", f"Created {role} account {created['name']}.",
                 ("user", user_id, created["name"]))
        self.commit()
        return self.account_json(created), password

    def update(self, user_id, data):
        """Edit a teacher or student: last_name / first_name / middle_initial (or name), grade +
        section (students), active, reset_password (with an optional password; empty = make one).
        Returns (account, new temporary password or None)."""
        account = self.users.get_account(user_id)
        if account is None:
            raise NotFoundError("Account not found.")
        new_password = None
        if data.get("reset_password"):
            new_password = check_new_account_password(str(data.get("password") or "")) \
                if data.get("password") else make_temp_password()
        if any(key in data for key in ("last_name", "first_name", "middle_initial", "name")):
            current = (account["last_name"], account["first_name"], account["middle_initial"])
            self.users.set_names(user_id, name_from_request(data, current))
        if account["role"] == "student" and ("grade" in data or "section" in data):
            merged = {"grade": account["grade"], "section": account["section"], **data}
            self.users.set_grade_section(user_id, *self.grade_section(merged, user_id))
        if "active" in data:
            self.users.set_active(user_id, bool(data["active"]))
        if new_password:
            self.set_temp_password(user_id, new_password)
        self.log_changes(account, self.users.get_account(user_id), new_password is not None)
        self.commit()
        return self.account_json(self.users.get_account(user_id)), new_password

    def log_changes(self, before, after, password_reset):
        """One activity log entry for each kind of change an edit made (nothing if it changed nothing).
        The new password is never written down."""
        target = ("user", after["id"], after["name"])
        if before["name"] != after["name"]:
            self.log("account.renamed", "accounts", f"Renamed {before['name']} to {after['name']}.", target)
        if (before["grade"], before["section"]) != (after["grade"], after["section"]):
            self.log("account.edited", "accounts", f"Changed the grade and section of {after['name']} to "
                     f"{' - '.join(filter(None, [after['grade'], after['section']])) or 'none'}.", target)
        if bool(before["active"]) != bool(after["active"]):
            enabled = bool(after["active"])
            self.log("account.activated" if enabled else "account.deactivated", "accounts",
                     f"{'Enabled' if enabled else 'Deactivated'} the account of {after['name']}.", target)
        if password_reset:
            self.log("account.password_reset", "accounts", f"Reset the password of {after['name']}.", target)

    def batch_update(self, data):
        """Change grade and/or section of many students at once. Students are user_ids, or
        match = {q, grade, name, section, status} for every student matching that search (all pages). A field not
        sent is kept; grade "" = no grade, section "" = no section (irregular).
        Returns how many students were changed."""
        ids = self.batch_ids(data, "change")
        if "grade" not in data and "section" not in data:
            raise ValidationError("Choose a grade or section to change.")

        grade = section = None
        if "grade" in data:
            grade = clean_grade_section({"grade": data["grade"]})[0]
            self.check_grade_enabled(grade)
        if "section" in data:
            section = clean_grade_section({"section": data["section"]})[1]
            if section:
                section = self.users.section_spelling(section) or section
        if grade is not None:
            self.users.set_grade_many(ids, grade)
        if section is not None:
            self.users.set_section_many(ids, section)
        self.log("account.batch_edited", "accounts", f"Changed the grade or section of {plural(len(ids), 'student')}.",
                 ("user", None, ""))
        self.commit()
        return len(ids)

    def batch_activate(self, data):
        """Enable many students at once (same selection as batch_update). Students already
        active are skipped. Returns {activated, skipped}."""
        ids = self.batch_ids(data, "activate")
        inactive = self.users.inactive_ids(ids)
        if inactive:
            self.users.activate_many(inactive)
            self.log("account.batch_activated", "accounts", f"Enabled {plural(len(inactive), 'student')}.",
                     ("user", None, ""))
            self.commit()
        return {"activated": len(inactive), "skipped": len(ids) - len(inactive)}

    def batch_delete(self, data):
        """Delete many students at once (same selection as batch_update). Only fresh students,
        never activated, can be deleted: an activated one is skipped even if deactivated now.
        Returns {deleted, skipped}."""
        ids = self.batch_ids(data, "delete")
        fresh = self.users.fresh_student_ids(ids)
        if fresh:
            self.users.delete_students(fresh)
            self.log("account.batch_deleted", "accounts", f"Deleted {plural(len(fresh), 'student')}.",
                     ("user", None, ""))
            self.commit()
        return {"deleted": len(fresh), "skipped": len(ids) - len(fresh)}

    def batch_ids(self, data, verb):
        """The students a batch request is about: user_ids, or match = {q, grade, name, section, status}
        for every student matching that search (all pages)."""
        if "match" in data and isinstance(data["match"], dict):
            match = data["match"]
            search = self.filters(match.get("q"), match.get("grade"), match.get("name"), match.get("section"),
                                  match.get("status"))
            ids = self.users.matching_ids("student", *search)
        else:
            ids = data.get("user_ids")
            if not isinstance(ids, list) or not all(isinstance(i, int) and not isinstance(i, bool) for i in ids):
                ids = []
        ids = sorted(set(ids))
        if not ids:
            raise ValidationError("Choose at least one student.")
        if len(ids) > MAX_BATCH:
            raise ValidationError(f"{verb.capitalize()} at most {MAX_BATCH} students at a time.")
        if self.users.count_students(ids) != len(ids):
            raise ValidationError(f"Only students can be {verb}d here.")
        return ids

    def set_temp_password(self, user_id, temp_password):
        self.users.set_password(user_id, generate_password_hash(temp_password), must_change_password=True)

    def grade_section(self, data, student_id=None):
        """(grade, section). A section typed in other capitals than an existing one ("rizal" when
        "Rizal" exists) takes the existing spelling, so the same section isn't listed twice."""
        grade, section = clean_grade_section(data)
        current = self.users.get_account(student_id)["grade"] if student_id else ""
        self.check_grade_enabled(grade, current)
        if section:
            section = self.users.section_spelling(section, student_id) or section
        return grade, section

    def check_grade_enabled(self, grade, current=""):
        """A disabled grade can't be given to anyone, except a student who already has it."""
        if grade and grade != current and grade in SettingsService(self.db).disabled_grades():
            raise ValidationError(f"{grade} is disabled. Choose another grade (Settings page).")

    def import_students(self, rows, dry_run):
        """Create student accounts from spreadsheet rows [(row number, {name, username, grade,
        section, password})]. All or nothing: with any bad row, no one is created and every
        problem is listed with its row number. dry_run only checks (the preview).
        A row whose name, grade and section match a student who already exists is skipped (so
        uploading the same file again creates no one) and listed in "existing".

        Returns {imported, students, existing, errors}. After a real import each student has their
        password (the one given, or a temporary one): it is shown once, like adding by hand."""
        errors, students, existing = [], [], []
        known = self.users.student_usernames_by_identity()
        given_usernames = {}  # username typed in the file -> first row with it
        sections = {}  # section in any capitals -> how it is spelled (school first, then this file)

        for number, record in rows:
            try:
                student = self.clean_import_row(number, record, given_usernames, sections, known)
                (existing if student.get("exists") else students).append(student)
            except ValidationError as problem:
                errors.append({"row": number, "message": problem.message})
        if errors:
            return {"imported": False, "students": [], "existing": [], "errors": errors}

        # Usernames left empty: made from the name, avoiding every username already taken
        # (in the school, or typed or made earlier in this file).
        used = set(given_usernames)
        for student in students:
            if not student["username"]:
                student["username"] = self.free_username(student["first_name"], student["last_name"], used)
            used.add(student["username"])

        skipped = [{key: student[key] for key in IMPORT_FIELDS} for student in existing]
        if dry_run:
            return {"imported": False, "errors": [], "existing": skipped, "students": [
                {key: student[key] for key in IMPORT_FIELDS} | {"password_given": bool(student["password"])}
                for student in students]}
        if not students:
            return {"imported": False, "errors": [], "existing": skipped, "students": []}

        created = []
        for student in students:
            password = student["password"] or make_temp_password()
            names = (student["last_name"], student["first_name"], student["middle_initial"])
            user_id = self.users.create(names, student["username"], generate_password_hash(password),
                                        "student", student["grade"], student["section"], active=False)
            created.append({key: student[key] for key in IMPORT_FIELDS}
                           | {"id": user_id, "password": password, "password_given": bool(student["password"])})
        self.log("account.imported", "accounts", f"Imported {plural(len(created), 'student')} from a file.",
                 ("user", None, ""))
        self.commit()
        return {"imported": True, "errors": [], "existing": skipped, "students": created}

    def clean_import_row(self, number, record, given_usernames, sections, known=None):
        """One spreadsheet row checked with the same rules as adding a student by hand.
        known = {(last, first, middle, grade, section) in lowercase: username} of the students who
        exist: a row matching one comes back with "exists" set and the existing username, and is
        not checked further.
        The name comes from Last name / First name / Middle initial columns, or one Name column
        written "Last, First" (with an optional ", M" or " M.")."""
        if record.get("last_name") or record.get("first_name") or not record.get("name"):
            last, first, middle = clean_person_name(record.get("last_name"), record.get("first_name"),
                                                    clean_middle_initial(record.get("middle_initial")))
        else:
            last, first, middle = split_full_name(record["name"])
        grade = grade_from_text(record["grade"])
        self.check_grade_enabled(grade)
        section = clean_name(record["section"])
        if len(section) > MAX_SECTION_LENGTH:
            raise ValidationError(f"Section can be at most {MAX_SECTION_LENGTH} characters.")
        if section:
            key = section.casefold()
            if key not in sections:
                sections[key] = self.users.section_spelling(section) or section
            section = sections[key]

        identity = tuple(part.casefold() for part in (last, first, middle, grade, section))
        if known and identity in known:
            return {"row": number, "name": display_name(last, first, middle), "last_name": last,
                    "first_name": first, "middle_initial": middle, "username": known[identity],
                    "grade": grade, "section": section, "exists": True}

        username = ""
        if record["username"]:
            username = clean_username(record["username"])
            if self.users.username_taken(username):
                raise ValidationError(f"The username \"{username}\" is already taken.")
            if username in given_usernames:
                raise ValidationError(f"The username \"{username}\" is used twice in the file "
                                      f"(rows {given_usernames[username]} and {number}).")
            given_usernames[username] = number
        password = str(record["password"])
        if password:
            check_new_account_password(password)
        return {"row": number, "name": display_name(last, first, middle), "last_name": last, "first_name": first,
                "middle_initial": middle, "username": username, "grade": grade, "section": section,
                "password": password}

    def free_username(self, first_name, last_name, used):
        """A username made from the name that nobody has: jdelacruz, jdelacruz2, jdelacruz3..."""
        name = display_name(last_name, first_name)
        base = suggest_username(first_name, last_name) or "student"
        candidates = ([base] if len(base) >= 3 else []) + [f"{base[:27]}{n}" for n in range(2, 10000)]
        for candidate in candidates:
            if candidate not in used and not self.users.username_taken(candidate):
                return candidate
        raise ValidationError(f"Could not make a username for {name}. Type one in the file.")

