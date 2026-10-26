from myguro.domain import feedback as rules
from myguro.errors import ForbiddenError, ValidationError
from myguro.repositories import FeedbackRepository
from myguro.services.base import Service


class FeedbackService(Service):
    """Teachers and students rate MyGuro; the admin reads the totals. Feedback is never written to
    the activity log, because the log names the person and the admin should not see who rated what."""

    def __init__(self, db, user=None):
        super().__init__(db, user)
        self.feedback = FeedbackRepository(db)

    def mine(self):
        """The questions, and whether this person already sent their feedback."""
        self.require_rater()
        return {"questions": [{"key": key, "text": text} for key, text in rules.QUESTIONS],
                "submitted": bool(self.feedback.mine(self.user["id"]))}

    def save(self, data):
        """{ratings: {question: 1-5}}: every question, sent once. A second try is refused, so the
        totals the admin reads cannot be changed afterwards."""
        self.require_rater()
        if self.feedback.mine(self.user["id"]):
            raise ValidationError("You already sent your feedback. Thank you!")
        ratings = rules.clean_ratings(data.get("ratings"))
        rules.require_every_question(ratings)
        for question, rating in ratings.items():
            self.feedback.save(self.user["id"], question, rating)
        self.commit()
        return {"submitted": True}

    def summary(self, role=""):
        """Admin: the average and how many gave each rating, per question. role = "teacher" or
        "student" to look at one group, else everyone. Holds no names."""
        if self.user["role"] != "admin":
            raise ForbiddenError("You don't have access to this.")
        if role and role not in rules.FEEDBACK_ROLES:
            raise ValidationError("Choose teachers, students, or everyone.")
        return rules.summarize(self.feedback.counts(role or None), self.feedback.respondents(role or None))

    def require_rater(self):
        if self.user["role"] not in rules.FEEDBACK_ROLES:
            raise ForbiddenError("Only teachers and students give feedback.")
