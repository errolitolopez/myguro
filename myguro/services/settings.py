import json

from myguro.domain.accounts import GRADES
from myguro.errors import ValidationError
from myguro.services.base import Service

GRADES_HIGH_TO_LOW = "grades_high_to_low"
DISABLED_GRADES = "disabled_grades"


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

    def get(self):
        disabled = self.disabled_grades()
        return {
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
        self.commit()
        return self.get()
