from myguro.domain import scoring
from myguro.errors import ValidationError
from myguro.repositories import (
    ActivityRepository, AssignmentRepository, ClassRepository, SchoolYearRepository, SettingsRepository,
    SubmissionRepository, UserRepository,
)


class Service:
    """A use case runs inside one service method: it checks the request, changes data through
    the repositories, and commits only when everything worked. On an error (myguro.errors) it
    stops, and nothing it changed is saved."""

    def __init__(self, db, user=None):
        self.db = db
        self.user = user  # the logged-in user's row
        self.users = UserRepository(db)
        self.classes = ClassRepository(db)
        self.activities = ActivityRepository(db)
        self.assignments = AssignmentRepository(db)
        self.submissions = SubmissionRepository(db)
        self.settings = SettingsRepository(db)
        self.years = SchoolYearRepository(db)

    def year_id(self):
        """The school year this person is looking at: the one they picked, else the current year."""
        picked = self.user["view_year_id"] if self.user is not None else None
        return picked if picked and self.years.get(picked) else self.years.current_id()

    def require_open_year(self, year_id):
        """A past school year can only be looked at: refuse changes to it."""
        if year_id != self.years.current_id():
            raise ValidationError("This school year is over. You can only look at it.")

    def commit(self):
        self.db.commit()

    def score(self, submission_id, activity_id):
        """Points of one attempt, per activity section and in total."""
        submission = self.submissions.get(submission_id)
        if submission and submission["paper"]:
            return scoring.paper_summary(submission["paper_score"], self.activities.total_points(activity_id))
        return scoring.summarize(self.submissions.score_rows(submission_id, activity_id))
