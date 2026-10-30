"""myguro: a Learning Management System for teachers and students.

Layers (each only uses the ones below it):
  web/           Flask blueprints: pages and JSON API, login/role checks
  services/      use cases (one class per area), commit when the work is done
  repositories/  all SQL, one class per kind of data
  domain/        rules with no Flask or SQL: cleaning input, checking answers, adding up scores
"""

from datetime import date

from flask import Flask, redirect, request, session, url_for

from myguro import commands, config, database, seed, seed_demo
from myguro.database import get_db
from myguro.domain.feedback import POPUP_ROLES as FEEDBACK_POPUP_ROLES
from myguro.domain.i18n import LANGUAGE_COOKIE, language_from_cookie, translate
from myguro.domain.support import popup_due
from myguro.errors import register_error_handlers
from myguro.i18n.tl import TAGLISH
from myguro.repositories import FeedbackRepository
from myguro.services import LoginThrottle, SchoolYearService, SettingsService
from myguro.web import BLUEPRINTS
from myguro.web.security import current_user


# Pages where the feedback pop-up never opens.
FEEDBACK_POPUP_SKIP_PAGES = {"student.answer_page", "feedback.page", "auth.change_password_page", "auth.login_page", None}


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    config.configure(app, test_config)

    database.init_app(app)
    app.cli.add_command(seed.seed_command)
    app.cli.add_command(seed_demo.seed_demo_command)
    app.cli.add_command(commands.backup_command)
    app.extensions["login_throttle"] = LoginThrottle()

    register_error_handlers(app)
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)

    @app.get("/favicon.ico")
    def favicon():
        """Browsers ask for /favicon.ico by themselves."""
        return redirect(url_for("static", filename="img/favicon.ico"))

    @app.context_processor
    def language():
        """The page's language, from the cookie the person's browser keeps (never the database). _() gives a
        template's English sentence in that language (English when it has no Taglish yet); TEXT_JSON is what
        the page's JavaScript needs for t(): the whole Taglish dictionary, or nothing in English."""
        chosen = language_from_cookie(request.cookies.get(LANGUAGE_COOKIE))
        dictionary = TAGLISH if chosen == "tl" else {}
        return {"LANG": chosen, "TEXT_JSON": dictionary,
                "_": lambda text, **values: translate(text, dictionary, values)}

    @app.context_processor
    def grade_options():
        """The grades for the dropdowns, in the order the admin chose (Settings page): GRADES are
        the ones that can be given to someone, ALL_GRADES also the disabled ones (for filters)."""
        settings = SettingsService(get_db())
        user = current_user()
        support = settings.support_for(user["role"]) if user else None
        # The window opens by itself for teachers, as often as the admin chose. The day it last
        # opened is kept in the login session, so a new login starts again.
        popup = False
        if support:
            today = date.today().isoformat()
            popup = popup_due(settings.popup_mode(user["role"]), session.get("support_popup_day"), today)
            if popup:
                session["support_popup_day"] = today
        # The feedback pop-up asks teachers and students who have not sent feedback yet, as often as the
        # admin chose. Not while the support window opens (one window at a time), not on the answer page
        # (nobody is interrupted mid-activity), and not on the feedback page itself.
        feedback_popup = False
        if (user and not popup and user["role"] in FEEDBACK_POPUP_ROLES
                and request.endpoint not in FEEDBACK_POPUP_SKIP_PAGES):
            mode = settings.feedback_popup_mode()
            if mode != "off" and not FeedbackRepository(get_db()).has_sent(user["id"]):
                today = date.today().isoformat()
                feedback_popup = popup_due(mode, session.get("feedback_popup_day"), today)
                if feedback_popup:
                    session["feedback_popup_day"] = today
        return {
            "GRADES": settings.grade_options(),
            "ALL_GRADES": settings.all_grade_options(),
            # The "Support myguro" link in the page footer: admin and teachers only, when turned on
            "SUPPORT": support,
            "SUPPORT_POPUP": popup,
            "FEEDBACK_POPUP": feedback_popup,
            # The navigation chat bubble: teachers only, and only while the admin has it on
            "CHATBOT": bool(user and user["role"] == "teacher" and settings.chatbot_enabled()),
            # The school years for the picker in the account menu (not on the login page)
            "SCHOOL_YEARS": SchoolYearService(get_db(), user).overview() if user and user["role"] != "supervisor" else None,
        }

    return app
