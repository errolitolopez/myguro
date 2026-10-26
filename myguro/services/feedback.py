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
        """The questions, and the ratings this person gave before."""
        self.require_rater()
        return {"questions": [{"key": key, "text": text} for key, text in rules.QUESTIONS],
                "ratings": self.feedback.mine(self.user["id"])}

    def save(self, data):
        """{ratings: {question: 1-5}}: keeps the person's earlier answers for questions not sent."""
        self.require_rater()
        ratings = rules.clean_ratings(data.get("ratings"))
        for question, rating in ratings.items():
            self.feedback.save(self.user["id"], question, rating)
        self.commit()
        return self.feedback.mine(self.user["id"])

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
