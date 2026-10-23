import json

from myguro.domain.accounts import GRADES
from myguro.domain.support import (DEFAULT_LABEL, DEFAULT_MESSAGE, DEFAULT_POPUP, POPUP_MODES, clean_support,
                                   format_gcash_number)
from myguro.errors import ValidationError
from myguro.services.base import Service

GRADES_HIGH_TO_LOW = "grades_high_to_low"
DISABLED_GRADES = "disabled_grades"
SUPPORT_KEYS = {"enabled": "support_enabled", "message": "support_message", "label": "support_label",
                "url": "support_url", "gcash_number": "support_gcash_number", "gcash_name": "support_gcash_name",
                "popup": "support_popup"}
SUPPORT_ROLES = ("admin", "teacher")  # students never see it
POPUP_ROLES = ("teacher",)  # the pop-up opens by itself for teachers only


class SettingsService(Service):
    """School-wide settings, changed by the admin and used by everyone."""

    def grades_high_to_low(self):
        """Grade dropdowns list Grade 12 first (on, the default) or Kinder first (off)."""
        return self.settings.get(GRADES_HIGH_TO_LOW) != "0"

    def disabled_grades(self):
        """The grades the school doesn't use: nobody can be given them (students who have one keep it)."""
        try:
            saved = json.loads(self.settings.get(DISABLED_GRADES) or "[]")
        except ValueError:
            saved = []
        return {grade for grade in saved if grade in GRADES}

    def all_grade_options(self):
        """Every grade, in the order the dropdowns show them (for filters, so a student in a
        disabled grade can still be found)."""
        return list(reversed(GRADES)) if self.grades_high_to_low() else list(GRADES)

    def grade_options(self):
        """The grades that can be given to someone, in the order the dropdowns show them."""
        disabled = self.disabled_grades()
        return [grade for grade in self.all_grade_options() if grade not in disabled]

    def support(self):
        """The support link as saved: {enabled, message, label, url}."""
        saved = {name: self.settings.get(key) for name, key in SUPPORT_KEYS.items()}
        return {
            "enabled": saved["enabled"] == "1",
            "message": saved["message"] or DEFAULT_MESSAGE,
            "label": saved["label"] or DEFAULT_LABEL,
            "url": saved["url"] or "",
            "gcash_number": saved["gcash_number"] or "",
            "gcash_display": format_gcash_number(saved["gcash_number"] or ""),
            "gcash_name": saved["gcash_name"] or "",
            "popup": saved["popup"] if saved["popup"] in POPUP_MODES else DEFAULT_POPUP,
        }

    def support_options(self, support):
        """The ways to give that are filled in, for the Support dialog: each {id, title, kind, ...}.
        A new way (more later) is one more entry here and one more block in the dialog."""
        options = []
        if support["url"]:
            options.append({"id": "kofi", "title": "Ko-fi", "kind": "link", "url": support["url"]})
        if support["gcash_number"]:
            options.append({"id": "gcash", "title": "GCash", "kind": "number", "number": support["gcash_number"],
                            "display": support["gcash_display"], "name": support["gcash_name"]})
        return options

    def support_for(self, role):
        """The support note to show a user of this role, or None (off, nothing to show, or a student)."""
        support = self.support()
        options = self.support_options(support)
        if role in SUPPORT_ROLES and support["enabled"] and options:
            return {**support, "options": options}
        return None

    def popup_mode(self, role):
        """When the support window opens by itself for this role ("off" for anyone but a teacher)."""
        return self.support()["popup"] if role in POPUP_ROLES else "off"

    def get(self):
        disabled = self.disabled_grades()
        return {
            "support": self.support(),
            "grades_high_to_low": self.grades_high_to_low(),
            "grades": [{"name": grade, "enabled": grade not in disabled} for grade in self.all_grade_options()],
        }

    def update(self, data):
        """Save the settings sent; the ones left out stay as they are."""
        if GRADES_HIGH_TO_LOW in data:
            value = data[GRADES_HIGH_TO_LOW]
            if not isinstance(value, bool):
                raise ValidationError("Choose on or off.")
            self.settings.set(GRADES_HIGH_TO_LOW, "1" if value else "0")
        if DISABLED_GRADES in data:
            grades = data[DISABLED_GRADES]
            if not isinstance(grades, list) or any(grade not in GRADES for grade in grades):
                raise ValidationError("Choose grades from the list.")
            self.settings.set(DISABLED_GRADES, json.dumps([grade for grade in GRADES if grade in grades]))
        if "support" in data:
            if not isinstance(data["support"], dict):
                raise ValidationError("Support link is not valid.")
            cleaned = clean_support(data["support"])
            for name, value in zip(SUPPORT_KEYS, cleaned):
                self.settings.set(SUPPORT_KEYS[name], ("1" if value else "0") if name == "enabled" else value)
        changed = [label for key, label in (("grades_high_to_low", "grade order"), ("disabled_grades", "grades in use"),
                                            ("support", "the support link")) if key in data]
        if changed:
            self.log("settings.changed", "settings", f"Changed settings: {', '.join(changed)}.")
        self.commit()
        return self.get()
