"""Use cases: one class per area. A service gets the database connection and the logged-in
user, checks the request with the domain rules, uses the repositories, and commits."""

from myguro.services.accounts import AccountService
from myguro.services.activities import ActivityService
from myguro.services.assignments import AssignmentService
from myguro.services.attendance import AttendanceService
from myguro.services.backups import BackupService
from myguro.services.auth import AuthService, LoginThrottle
from myguro.services.classes import ClassService
from myguro.services.dashboard import DashboardService
from myguro.services.feedback import FeedbackService
from myguro.services.gradebook import GradebookService
from myguro.services.log import LogService
from myguro.services.results import ResultsService
from myguro.services.schedule import ScheduleService
from myguro.services.school_years import SchoolYearService
from myguro.services.settings import SettingsService
from myguro.services.student_work import StudentWorkService

__all__ = ["AccountService", "ActivityService", "AssignmentService", "AttendanceService", "AuthService", "BackupService", "ClassService",
           "DashboardService", "FeedbackService", "GradebookService", "LoginThrottle", "LogService", "ResultsService", "ScheduleService", "SchoolYearService", "SettingsService", "StudentWorkService"]
