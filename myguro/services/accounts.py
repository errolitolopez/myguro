from werkzeug.security import generate_password_hash

from myguro.domain.accounts import (
    ACCOUNT_ROLES, check_name, check_new_account_password, clean_grade_section, clean_username, make_temp_password,
)
from myguro.domain.text import clean_name
from myguro.errors import NotFoundError, ValidationError
from myguro.services.base import Service
from myguro.services.presenters import user_json


class AccountService(Service):
    """The admin's work on teacher and student accounts (there is no sign-up)."""

    def account_json(self, row):
        """user_json plus the role and how many classes the teacher teaches or the student is in."""
        return {**user_json(row), "role": row["role"], "classes": self.users.count_classes(row)}

    def list(self, role):
        if role not in ACCOUNT_ROLES:
            raise ValidationError("Unknown role.")
        return [self.account_json(row) for row in self.users.list_by_role(role)]

    def create(self, data):
        """Create a teacher or student. Returns (account, temporary password): the password is
        shown once so the admin can give it; they must change it on first login."""
        role = data.get("role", "teacher")
        if role not in ACCOUNT_ROLES:
            raise ValidationError("Unknown role.")
        name = check_name(clean_name(data.get("name")))
        grade, section = "", ""
        if role == "student":
            grade, section = self.grade_section(data)
        username = clean_username(data.get("username"))
        password = check_new_account_password(str(data.get("password", "")) or make_temp_password())
        if self.users.username_taken(username):
            raise ValidationError(f"The username \"{username}\" is already taken.")
        user_id = self.users.create(name, username, generate_password_hash(password), role, grade, section)
        self.commit()
        return self.account_json(self.users.get(user_id)), password

    def update(self, user_id, data):
        """Edit a teacher or student: name, grade + section (students), active, reset_password.
        Returns (account, new temporary password or None)."""
        account = self.users.get_account(user_id)
        if account is None:
            raise NotFoundError("Account not found.")
        if "name" in data:
            self.users.set_name(user_id, check_name(clean_name(data["name"])))
        if account["role"] == "student" and ("grade" in data or "section" in data):
            merged = {"grade": account["grade"], "section": account["section"], **data}
            self.users.set_grade_section(user_id, *self.grade_section(merged, user_id))
        if "active" in data:
            self.users.set_active(user_id, bool(data["active"]))
        temp_password = self.reset_password(user_id) if data.get("reset_password") else None
        self.commit()
        return self.account_json(self.users.get_account(user_id)), temp_password

    def reset_password(self, user_id):
        temp_password = make_temp_password()
        self.users.set_password(user_id, generate_password_hash(temp_password), must_change_password=True)
        return temp_password

    def grade_section(self, data, student_id=None):
        """(grade, section). A section typed in other capitals than an existing one ("rizal" when
        "Rizal" exists) takes the existing spelling, so the same section isn't listed twice."""
        grade, section = clean_grade_section(data)
        if section:
            section = self.users.section_spelling(section, student_id) or section
        return grade, section
