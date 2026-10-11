"""Use cases: one class per area. A service gets the database connection and the logged-in
user, checks the request with the domain rules, uses the repositories, and commits."""

from myguro.services.accounts import AccountService
from myguro.services.activities import ActivityService
from myguro.services.assignments import AssignmentService
from myguro.services.auth import AuthService, LoginThrottle
from myguro.services.classes import ClassService
from myguro.services.dashboard import DashboardService
from myguro.services.results import ResultsService
from myguro.services.settings import SettingsService
from myguro.services.student_work import StudentWorkService

__all__ = ["AccountService", "ActivityService", "AssignmentService", "AuthService", "ClassService",
           "DashboardService", "LoginThrottle", "ResultsService", "SettingsService", "StudentWorkService"]
