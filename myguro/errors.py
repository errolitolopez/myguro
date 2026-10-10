"""Errors the services raise when a request can't be done. The web layer turns them into
JSON answers like {"error": "Title is required."} with the right HTTP status."""

from flask import jsonify


class AppError(Exception):
    status = 400

    def __init__(self, message, **extra):
        super().__init__(message)
        self.message = message
        self.extra = extra  # more fields for the JSON answer


class ValidationError(AppError):
    """The request has bad or missing data (400)."""
    status = 400


class NotFoundError(AppError):
    """It doesn't exist, or it isn't yours (404)."""
    status = 404


class ForbiddenError(AppError):
    """You may not do this (403)."""
    status = 403


class UnauthorizedError(AppError):
    """Not logged in, or the wrong password (401)."""
    status = 401


class TooManyRequestsError(AppError):
    """Too many wrong passwords (429)."""
    status = 429


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(error):
        # Nothing of a failed request is saved: the connection closes without commit.
        return jsonify(error=error.message, **error.extra), error.status
