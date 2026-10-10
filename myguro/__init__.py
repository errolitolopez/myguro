"""myguro: learning activity sheets for teachers and students.

Layers (each only uses the ones below it):
  web/           Flask blueprints: pages and JSON API, login/role checks
  services/      use cases (one class per area), commit when the work is done
  repositories/  all SQL, one class per kind of data
  domain/        rules with no Flask or SQL: cleaning input, checking answers, adding up scores
"""

from flask import Flask

from myguro import config, database, seed
from myguro.domain.accounts import GRADES
from myguro.errors import register_error_handlers
from myguro.services import LoginThrottle
from myguro.web import BLUEPRINTS


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    config.configure(app, test_config)

    database.init_app(app)
    app.cli.add_command(seed.seed_command)
    app.extensions["login_throttle"] = LoginThrottle()

    register_error_handlers(app)
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)
    app.jinja_env.globals["GRADES"] = GRADES
    return app
