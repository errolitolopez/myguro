from myguro.domain import scoring
from myguro.repositories import (
    ActivityRepository, AssignmentRepository, ClassRepository, SettingsRepository, SubmissionRepository,
    UserRepository,
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

    def commit(self):
        self.db.commit()

    def score(self, submission_id, activity_id):
        """Points of one attempt, per activity section and in total."""
        submission = self.submissions.get(submission_id)
        if submission and submission["paper"]:
            return scoring.paper_summary(submission["paper_score"], self.activities.total_points(activity_id))
        return scoring.summarize(self.submissions.score_rows(submission_id, activity_id))
