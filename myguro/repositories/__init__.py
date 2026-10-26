"""Data access: every SQL query lives in these classes. Each takes the database connection;
none of them commits (the service decides when the work is done)."""

from myguro.repositories.activities import ActivityRepository
from myguro.repositories.assignments import AssignmentRepository
from myguro.repositories.attendance import AttendanceRepository
from myguro.repositories.classes import ClassRepository
from myguro.repositories.feedback import FeedbackRepository
from myguro.repositories.log import LogRepository
from myguro.repositories.schedule import ScheduleRepository
from myguro.repositories.school_years import SchoolYearRepository
from myguro.repositories.settings import SettingsRepository
from myguro.repositories.submissions import SubmissionRepository
from myguro.repositories.users import UserRepository

__all__ = ["ActivityRepository", "AssignmentRepository", "AttendanceRepository", "ClassRepository", "FeedbackRepository", "LogRepository", "ScheduleRepository", "SchoolYearRepository",
           "SettingsRepository", "SubmissionRepository", "UserRepository"]
