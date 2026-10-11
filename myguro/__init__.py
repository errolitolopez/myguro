"""myguro: learning activity sheets for teachers and students.

Layers (each only uses the ones below it):
  web/           Flask blueprints: pages and JSON API, login/role checks
  services/      use cases (one class per area), commit when the work is done
  repositories/  all SQL, one class per kind of data
  domain/        rules with no Flask or SQL: cleaning input, checking answers, adding up scores
"""

from flask import Flask, redirect, url_for

from myguro import config, database, seed
from myguro.database import get_db
from myguro.errors import register_error_handlers
from myguro.services import LoginThrottle, SettingsService
from myguro.web import BLUEPRINTS
from myguro.web.security import current_user


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    config.configure(app, test_config)

    database.init_app(app)
    app.cli.add_command(seed.seed_command)
    app.extensions["login_throttle"] = LoginThrottle()

    register_error_handlers(app)
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)

    @app.get("/favicon.ico")
    def favicon():
        """Browsers ask for /favicon.ico by themselves."""
        return redirect(url_for("static", filename="img/favicon.ico"))

    @app.context_processor
    def grade_options():
        """The grades for the dropdowns, in the order the admin chose (Settings page): GRADES are
        the ones that can be given to someone, ALL_GRADES also the disabled ones (for filters)."""
        settings = SettingsService(get_db())
        user = current_user()
        return {
            "GRADES": settings.grade_options(),
            "ALL_GRADES": settings.all_grade_options(),
            # The "Support myguro" link in the page footer: admin and teachers only, when turned on
            "SUPPORT": settings.support_for(user["role"]) if user else None,
        }

    return app
