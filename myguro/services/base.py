from myguro.domain import scoring
from myguro.domain import log as log_rules
from myguro.domain.log import CATEGORIES, clean_summary
from myguro.errors import ValidationError
from myguro.repositories import (
    ActivityRepository, AssignmentRepository, ClassRepository, LogRepository, SchoolYearRepository,
    SettingsRepository, SubmissionRepository, UserRepository,
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
        self.logs = LogRepository(db)

    def year_id(self):
        """The school year this person is looking at: the one they picked, else the current year."""
        picked = self.user["view_year_id"] if self.user is not None else None
        return picked if picked and self.years.get(picked) else self.years.current_id()

    def require_open_year(self, year_id):
        """A past school year can only be looked at: refuse changes to it."""
        if year_id != self.years.current_id():
            raise ValidationError("This school year is over. You can only look at it.")

    def log(self, action, category, summary, target=("", None, ""), actor=None, address=""):
        """Add an activity log entry for what this service call did. Call it right before commit(), so
        the entry and the change are saved together (a failed change leaves no entry). actor is the
        logged-in user unless given; target = (type, id, name). Never put a password in the summary."""
        assert category in CATEGORIES, category
        who = actor if actor is not None else self.user
        self.logs.add({"id": who["id"], "name": who["name"], "username": who["username"], "role": who["role"]},
                      action, category, clean_summary(summary), *target, address=address)
        self.logs.trim(log_rules.MAX_LOG_ENTRIES)  # keeps the log from growing without end

    def commit(self):
        self.db.commit()

    def score(self, submission_id, activity_id):
        """Points of one attempt, per activity section and in total."""
        submission = self.submissions.get(submission_id)
        if submission and submission["paper"]:
            return scoring.paper_summary(submission["paper_score"], self.activities.total_points(activity_id))
        return scoring.summarize(self.submissions.score_rows(submission_id, activity_id))
