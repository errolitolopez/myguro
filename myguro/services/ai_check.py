from myguro import ai_check_client
from myguro.config import school_today
from myguro.domain import ai_check as rules
from myguro.errors import NotFoundError, ValidationError
from myguro.repositories import AiCheckRepository
from myguro.services.results import ResultsService
from myguro.services.settings import SettingsService


class AiCheckService(ResultsService):
    """Check with AI: for one short answer, a suggested score and a short explanation. It changes no score: the
    teacher decides and saves. Only the question, the guide, the points and the answer are sent, never names."""

    def __init__(self, db, user=None):
        super().__init__(db, user)
        self.usage = AiCheckRepository(db)

    def suggest(self, submission_id, question_id):
        """{points, explanation, max_points} for a short answer of a submitted attempt. Not found while the admin has
        it off, so it looks like it does not exist."""
        if not SettingsService(self.db, self.user).ai_check_enabled():
            raise NotFoundError("Page not found.")
        submission = self.require_submission(submission_id)
        if not submission["submitted_at"]:
            raise ValidationError("The student hasn't submitted this attempt yet.")
        if submission["paper"]:
            raise ValidationError("This is a paper score: change its total instead.")
        questions = self.activities.questions(submission["activity_id"])
        number, question = next(((index, item) for index, item in enumerate(questions, start=1)
                                 if item["id"] == question_id and item["type"] == "short_answer"), (0, None))
        if question is None:
            raise NotFoundError("Question not found.")
        answer = self.submissions.answers(submission_id).get(question_id)
        if not answer:
            raise ValidationError("The student left this answer empty.")
        today = school_today().isoformat()
        if self.usage.count_today(self.user["id"], today) >= rules.MAX_PER_DAY:
            raise ValidationError("You reached today's limit. Try again tomorrow.")
        # Counted before the call, so a failing service cannot be used to send without limit
        self.usage.add_one(self.user["id"], today)
        self.commit()
        reply = ai_check_client.ask_model(rules.build_request(question["prompt"], question["answer"],
                                                              question["points"], answer))
        suggestion = rules.clean_suggestion(reply, question["points"])
        if suggestion is None:
            raise ValidationError("The AI check is not available right now.")
        # The log says that it was used, never what was sent or said
        self.log_checking("checking.ai_check", f"Asked the AI to check question {number} of "
                          f"{self.student_name(submission['student_id'])}.",
                          submission["assignment_id"], submission["student_id"])
        self.commit()
        return {"points": suggestion[0], "explanation": suggestion[1], "max_points": question["points"]}
