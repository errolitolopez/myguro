"""The Flask side: one blueprint per area (pages + JSON API), kept thin. A route reads the
request, calls a service, and returns JSON or a page; errors from services become JSON answers
(myguro.errors)."""

from myguro.web import (accounts, activities, auth, classes, dashboard, log, results, school_years, settings,
                        student)

BLUEPRINTS = [auth.bp, dashboard.bp, accounts.bp, classes.bp, activities.bp, student.bp, results.bp,
              settings.bp, school_years.bp, log.bp]
