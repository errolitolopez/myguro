"""Errors the services raise when a request can't be done. The web layer turns them into
JSON answers like {"error": "Title is required."} with the right HTTP status."""

from flask import jsonify, render_template, request


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
    @app.errorhandler(413)
    def handle_too_big(error):
        megabytes = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
        return jsonify(error=f"The file is too big (at most {megabytes} MB)."), 413

    @app.errorhandler(404)
    def handle_not_found(error):
        # The pages call /api/... and read JSON; a person who typed a wrong address gets a page
        return error_response(404, "Page not found",
                              "The page you are looking for does not exist, or the address is wrong.", "Not found.")

    @app.errorhandler(405)
    def handle_not_allowed(error):
        return error_response(405, "Not allowed", "This address does not accept that kind of request.",
                              "This is not allowed here.")

    @app.errorhandler(500)
    def handle_crash(error):
        """A bug or a broken server: Flask has already written the details to the server log. The person
        only gets a short, calm message, never a traceback."""
        return error_response(500, "Something went wrong",
                              "Please try again in a moment. If it keeps happening, tell your admin.",
                              "Something went wrong. Please try again.")

    @app.errorhandler(AppError)
    def handle_app_error(error):
        # Nothing of a failed request is saved: the connection closes without commit.
        return jsonify(error=error.message, **error.extra), error.status


# Shown if even the error page cannot be drawn (for example the database is the thing that broke).
PLAIN_PAGE = ("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width, initial-scale=1'>"
              "<title>MyGuro</title><body style='font-family:sans-serif;text-align:center;padding:3rem 1rem'>"
              "<h1>Something went wrong</h1><p>Please try again in a moment.</p><p><a href='/'>Go to MyGuro</a></p>")


def error_response(status, title, message, api_message):
    """The answer for an error: JSON for the /api/ calls the pages make, a MyGuro page for a person."""
    if request.path.startswith("/api/"):
        return jsonify(error=api_message), status
    try:
        return render_template("error.html", status=status, title=title, message=message), status
    except Exception:
        return PLAIN_PAGE, status
