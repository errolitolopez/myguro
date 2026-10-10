"""Data access: every SQL query lives in these classes. Each takes the database connection;
none of them commits (the service decides when the work is done)."""

from myguro.repositories.activities import ActivityRepository
from myguro.repositories.assignments import AssignmentRepository
from myguro.repositories.classes import ClassRepository
from myguro.repositories.submissions import SubmissionRepository
from myguro.repositories.users import UserRepository

__all__ = ["ActivityRepository", "AssignmentRepository", "ClassRepository", "SubmissionRepository",
           "UserRepository"]
