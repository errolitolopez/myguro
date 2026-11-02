"""The Flask side: one blueprint per area (pages + JSON API), kept thin. A route reads the
request, calls a service, and returns JSON or a page; errors from services become JSON answers
(myguro.errors)."""

from myguro.web import (accounts, activities, auth, backup, chat, classes, dashboard, display, feedback, holidays, log, notifications, recovery, results, school_years, schedule, settings,
                        student, time_clock)

BLUEPRINTS = [auth.bp, dashboard.bp, accounts.bp, classes.bp, activities.bp, student.bp, results.bp,
              settings.bp, school_years.bp, log.bp, backup.bp, chat.bp, schedule.bp, feedback.bp, holidays.bp, display.bp, recovery.bp, notifications.bp, time_clock.bp]
