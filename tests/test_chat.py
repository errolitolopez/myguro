"""The navigation chatbot: the admin switch, the teacher-only chat, and its strict limits."""

from conftest import error, login


def chatbot_setting(client):
    return client.get("/api/settings").get_json()["settings"]["chatbot_enabled"]


def test_off_by_default_and_admin_turns_it_on_and_off(admin):
    assert chatbot_setting(admin) is False
    assert admin.put("/api/settings", json={"chatbot_enabled": True}).get_json()["settings"]["chatbot_enabled"] is True
    # saved in the database: a new session sees it too
    assert chatbot_setting(login("admin", "adminpass1")) is True
    assert admin.put("/api/settings", json={"chatbot_enabled": False}).get_json()["settings"]["chatbot_enabled"] is False


def test_only_admin_changes_it_and_value_must_be_on_or_off(admin, teacher):
    assert teacher.put("/api/settings", json={"chatbot_enabled": True}).status_code == 403
    assert error(admin.put("/api/settings", json={"chatbot_enabled": "yes"})) == "Choose on or off."
    assert chatbot_setting(admin) is False


def test_change_is_in_the_activity_log(admin):
    admin.put("/api/settings", json={"chatbot_enabled": True})
    entries = admin.get("/api/log?category=settings").get_json()["entries"]
    assert any("the chatbot" in entry["summary"] for entry in entries)


# --- The chat itself. The call to the AI service is replaced, so no test uses the network. ---

import pytest

from myguro import chat_client
from myguro.domain import chat as rules


@pytest.fixture
def asked(monkeypatch):
    """Replaces the AI call. Set asked.key to what the "model" picks; asked.calls holds what was sent."""
    class Fake:
        key = "classes"
        calls = []
        histories = []

    def fake(message, pages, prompt, history=()):
        Fake.calls.append((message, list(pages), prompt))
        Fake.histories.append(list(history))
        return Fake.key

    Fake.calls = []
    Fake.histories = []
    monkeypatch.setattr(chat_client, "ask_model", fake)
    return Fake


@pytest.fixture
def chat_on(admin):
    admin.put("/api/settings", json={"chatbot_enabled": True})


def say(client, message="where are my classes?"):
    return client.post("/api/chat", json={"message": message})


def test_off_by_default_teacher_gets_404_and_nothing_is_sent(teacher, asked):
    assert say(teacher).status_code == 404
    assert asked.calls == []


def test_teacher_gets_a_link_from_the_list(teacher, chat_on, asked):
    data = say(teacher).get_json()
    assert data["link"] == {"label": "Open Classes", "url": "/classes"}
    assert data["reply"].startswith("Here is Classes.")


def test_every_link_in_the_list_is_a_real_teacher_page(teacher, chat_on, asked):
    for key, (_, path, _, _) in rules.TEACHER_PAGES.items():
        teacher.delete("/api/chat/history")  # a chat holds only a few questions
        asked.key = key
        assert say(teacher).get_json()["link"]["url"] == path
        assert teacher.get(path).status_code == 200, path


@pytest.mark.parametrize("picked", ["none", "../admin", "/users", "https://example.com", "", 5])
def test_unknown_key_or_no_page_gets_the_fixed_reply(teacher, chat_on, asked, picked):
    asked.key = picked
    data = say(teacher).get_json()
    assert (data["reply"], data["link"]) == (rules.NO_PAGE_REPLY, None)


def test_service_not_available_gets_a_plain_reply(teacher, chat_on, asked):
    asked.key = None
    data = say(teacher).get_json()
    assert (data["reply"], data["link"]) == (rules.UNAVAILABLE_REPLY, None)


def test_no_api_key_means_not_available(teacher, chat_on, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert say(teacher).get_json()["link"] is None


def test_only_the_question_and_the_page_list_are_sent(teacher, chat_on, asked):
    say(teacher, "  where   are my classes? ")
    (message, keys, prompt), = asked.calls
    assert message == "where are my classes?"
    assert keys == list(rules.TEACHER_TOPICS)
    # no names or account details of the teacher in what the model gets
    assert "Santos" not in prompt and "msantos" not in prompt


def test_other_roles_get_404_even_when_on(admin, chat_on, asked, supervisor):
    from conftest import login
    assert say(admin).status_code == 404
    assert say(supervisor).status_code == 404
    assert asked.calls == []


def test_logged_out_is_refused(chat_on, app):
    assert app.test_client().post("/api/chat", json={"message": "hi"}).status_code == 401


def test_message_must_be_there_and_short(teacher, chat_on, asked):
    assert error(say(teacher, "   ")) == "Write what you are looking for."
    assert error(teacher.post("/api/chat", json={})) == "Write what you are looking for."
    assert error(say(teacher, "x" * (rules.MAX_MESSAGE_LENGTH + 1))) == "Write a shorter question."
    assert say(teacher, "x" * rules.MAX_MESSAGE_LENGTH).status_code == 200
    assert len(asked.calls) == 1


def test_daily_limit_then_next_day_works(teacher, chat_on, asked, monkeypatch):
    from datetime import date
    from myguro.services import chat as chat_service
    monkeypatch.setattr(rules, "MAX_MESSAGES_PER_DAY", 3)
    for _ in range(3):
        assert say(teacher).status_code == 200
    assert error(say(teacher)) == "You reached today's limit. Try again tomorrow."
    assert len(asked.calls) == 3
    monkeypatch.setattr(chat_service, "school_today", lambda: date(2099, 1, 1))
    assert say(teacher).status_code == 200


def test_history_is_saved_for_that_teacher_only(teacher, other_teacher, chat_on, asked):
    assert teacher.get("/api/chat/history").get_json() == {"questions_left": rules.MAX_QUESTIONS_PER_CHAT, "suggestions": rules.SUGGESTIONS, "messages": []}
    say(teacher, "where are my classes?")
    asked.key = "none"
    say(teacher, "tell me a joke")
    messages = teacher.get("/api/chat/history").get_json()["messages"]
    assert [(m["sender"], m["text"]) for m in messages] == [
        ("teacher", "where are my classes?"), ("bot", "Here is Classes. Open a class there to find its gradebook and attendance."),
        ("teacher", "tell me a joke"), ("bot", rules.NO_PAGE_REPLY)]
    assert messages[1]["link"] == {"label": "Open Classes", "url": "/classes"} and messages[3]["link"] is None
    assert other_teacher.get("/api/chat/history").get_json()["messages"] == []


def test_latest_messages_are_sent_so_it_can_follow_up(teacher, chat_on, asked):
    asked.key = "how-new-class"
    say(teacher, "first question")
    say(teacher, "and then?")
    assert asked.histories[0] == []
    # the teacher's question and only the title line of the reply, not the steps
    assert asked.histories[1] == [("teacher", "first question"), ("bot", "How to: Create a class")]
    assert "first question" not in asked.calls[1][2]  # never inside the prompt


def test_only_the_latest_few_messages_are_sent(teacher, chat_on, asked, monkeypatch):
    monkeypatch.setattr(rules, "MAX_CONTEXT_MESSAGES", 3)
    for number in range(4):
        say(teacher, f"question {number}")
    # 3 messages = bot, teacher, bot: the leading bot message is dropped so it starts with the teacher
    assert [text for sender, text in asked.histories[3] if sender == "teacher"] == ["question 2"]


def test_other_teachers_chat_is_never_sent(teacher, other_teacher, chat_on, asked):
    say(other_teacher, "private question")
    say(teacher, "my question")
    assert asked.histories[1] == []


def test_refused_messages_are_not_saved(teacher, chat_on, asked):
    say(teacher, "   ")
    say(teacher, "x" * (rules.MAX_MESSAGE_LENGTH + 1))
    assert teacher.get("/api/chat/history").get_json() == {"questions_left": rules.MAX_QUESTIONS_PER_CHAT, "suggestions": rules.SUGGESTIONS, "messages": []}


def test_a_chat_holds_five_questions_then_must_be_deleted(teacher, chat_on, asked):
    for number in range(rules.MAX_QUESTIONS_PER_CHAT):
        data = say(teacher, f"question {number}").get_json()
        assert data["questions_left"] == rules.MAX_QUESTIONS_PER_CHAT - number - 1
    response = say(teacher, "one more")
    assert response.status_code == 400
    assert response.get_json() == {"error": rules.CHAT_FULL_MESSAGE, "questions_left": 0}
    assert len(asked.calls) == rules.MAX_QUESTIONS_PER_CHAT  # nothing was sent to the model
    history = teacher.get("/api/chat/history").get_json()
    assert history["questions_left"] == 0 and len(history["messages"]) == 2 * rules.MAX_QUESTIONS_PER_CHAT
    # deleting the chat starts a new one
    assert teacher.delete("/api/chat/history").get_json() == {"questions_left": rules.MAX_QUESTIONS_PER_CHAT, "suggestions": rules.SUGGESTIONS, "messages": []}
    assert say(teacher, "fresh start").get_json()["questions_left"] == rules.MAX_QUESTIONS_PER_CHAT - 1


def test_a_full_chat_does_not_use_the_daily_limit_or_block_others(teacher, other_teacher, chat_on, asked):
    for number in range(rules.MAX_QUESTIONS_PER_CHAT):
        say(teacher, f"q{number}")
    say(teacher, "refused")
    assert say(other_teacher, "my own chat").status_code == 200


def test_the_model_gets_the_whole_chat_so_far(teacher, chat_on, asked):
    for number in range(rules.MAX_QUESTIONS_PER_CHAT):
        say(teacher, f"q{number}")
    assert len([1 for sender, _ in asked.histories[-1] if sender == "teacher"]) == rules.MAX_QUESTIONS_PER_CHAT - 1


def test_teacher_clears_their_history(teacher, other_teacher, chat_on, asked):
    say(teacher, "mine")
    say(other_teacher, "theirs")
    assert teacher.delete("/api/chat/history").get_json()["messages"] == []
    assert teacher.get("/api/chat/history").get_json() == {"questions_left": rules.MAX_QUESTIONS_PER_CHAT, "suggestions": rules.SUGGESTIONS, "messages": []}
    assert len(other_teacher.get("/api/chat/history").get_json()["messages"]) == 2


def test_history_is_closed_to_other_roles_and_when_off(teacher, admin, supervisor, chat_on, asked, app):
    for client in (admin, supervisor):
        assert client.get("/api/chat/history").status_code == 404
        assert client.delete("/api/chat/history").status_code == 404
    assert app.test_client().get("/api/chat/history").status_code == 401
    say(teacher)
    admin.put("/api/settings", json={"chatbot_enabled": False})
    assert teacher.get("/api/chat/history").status_code == 404


def test_history_is_not_in_the_activity_log(admin, teacher, chat_on, asked):
    say(teacher, "secretword please")
    assert "secretword" not in str(admin.get("/api/log?per_page=100").get_json())


def test_bubble_only_for_a_teacher_when_on(teacher, admin, app):
    assert 'id="chat-bubble"' not in teacher.get("/dashboard").get_data(as_text=True)
    admin.put("/api/settings", json={"chatbot_enabled": True})
    page = teacher.get("/dashboard").get_data(as_text=True)
    assert 'id="chat-bubble"' in page and "js/chat.js" in page
    assert 'id="chat-bubble"' not in admin.get("/dashboard").get_data(as_text=True)
    admin.put("/api/settings", json={"chatbot_enabled": False})
    assert 'id="chat-bubble"' not in teacher.get("/dashboard").get_data(as_text=True)


def test_bubble_not_on_the_login_page(chat_on, app):
    assert 'id="chat-bubble"' not in app.test_client().get("/login").get_data(as_text=True)


def test_gemini_request_and_answer_shape(monkeypatch):
    """The real client with the network replaced: forced help call, key in a header, page read back."""
    import io, json, urllib.request
    seen = {}

    def fake_urlopen(request, timeout):
        seen["body"] = json.loads(request.data)
        seen["key"] = request.get_header("X-goog-api-key")
        reply = {"candidates": [{"content": {"parts": [{"functionCall": {"name": "help", "args": {"key": "classes"}}}]}}]}
        return io.BytesIO(json.dumps(reply).encode())

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert chat_client.ask_model("my classes", rules.TEACHER_TOPICS, "prompt") == "classes"
    assert seen["key"] == "test-key"
    assert seen["body"]["toolConfig"]["functionCallingConfig"]["allowedFunctionNames"] == ["help"]
    assert seen["body"]["contents"][0]["parts"][0]["text"] == "my classes"
    assert seen["body"]["tools"][0]["functionDeclarations"][0]["parameters"]["properties"]["key"]["enum"][-2:] == ["none", "admin-only"]


# --- How-to guides ---

from myguro.domain.chat_guides import TEACHER_GUIDES


def test_every_guide_has_steps_and_starts_on_a_real_page():
    for key, (title, about, page, steps) in TEACHER_GUIDES.items():
        assert key.startswith("how-") and key not in rules.TEACHER_PAGES
        assert title and about and steps, key
        assert page in rules.TEACHER_PAGES, key


def test_teacher_gets_the_written_steps_and_a_button(teacher, chat_on, asked):
    asked.key = "how-new-class"
    data = say(teacher, "how do I make a class?").get_json()
    title, _, _, steps = TEACHER_GUIDES["how-new-class"]
    assert data["reply"] == f"How to: {title}\n" + "\n".join(f"{n}. {step}" for n, step in enumerate(steps, 1))
    assert data["link"] == {"label": "Open Classes", "url": "/classes"}
    # saved in the history with its button
    saved = teacher.get("/api/chat/history").get_json()["messages"][-1]
    assert saved["text"] == data["reply"] and saved["link"] == data["link"]


def test_every_guide_works_through_the_chat(teacher, chat_on, asked):
    for key in TEACHER_GUIDES:
        teacher.delete("/api/chat/history")  # a chat holds only a few questions
        asked.key = key
        data = say(teacher).get_json()
        assert data["reply"].startswith("How to: ") and data["link"]["url"].startswith("/")


def test_guides_and_pages_are_what_the_model_is_offered(teacher, chat_on, asked):
    say(teacher)
    _, keys, prompt = asked.calls[0]
    assert set(rules.TEACHER_PAGES) | set(TEACHER_GUIDES) == set(keys)
    assert all(f'"{key}"' in prompt for key in keys)


def test_bubble_has_the_size_button(teacher, chat_on):
    page = teacher.get("/dashboard").get_data(as_text=True)
    assert 'id="chat-size"' in page and 'aria-label="Make the chat window bigger"' in page


def test_admin_only_questions_say_to_ask_the_admin(teacher, chat_on, asked):
    asked.key = "admin-only"
    data = say(teacher, "what page to delete a user?").get_json()
    assert (data["reply"], data["link"]) == (rules.ADMIN_ONLY_REPLY, None)


def test_the_model_is_told_about_admin_only_and_none(teacher, chat_on, asked):
    say(teacher)
    prompt = asked.calls[0][2]
    assert '"admin-only"' in prompt and '"none"' in prompt and "delet" in prompt


def test_the_editor_has_a_bottom_bar_the_bubble_must_clear(teacher, chat_on):
    """The CSS lifts the bubble above any page with a fixed or sticky bottom bar (browser check: see the checklist)."""
    css = open("myguro/static/css/glass.css").read()
    assert "--chat-lift: 3.75rem" in css and "body:has(.position-fixed.bottom-0)" in css
    sheet = teacher.post("/api/activities", json={"title": "Test", "subject": "Math"}).get_json()
    page = teacher.get(f"/activities/{sheet['activity']['id']}").get_data(as_text=True)
    assert "position-fixed bottom-0" in page and 'id="chat-bubble"' in page


def test_suggestions_come_with_the_history_and_are_valid_questions(teacher, chat_on, asked):
    data = teacher.get("/api/chat/history").get_json()
    assert data["suggestions"] == rules.SUGGESTIONS and len(rules.SUGGESTIONS) >= 3
    assert all(0 < len(text) <= rules.MAX_MESSAGE_LENGTH for text in rules.SUGGESTIONS)
    assert len(set(rules.SUGGESTIONS)) == len(rules.SUGGESTIONS)
    # tapping one is an ordinary question: it goes through the same route and the same limits
    assert say(teacher, rules.SUGGESTIONS[0]).status_code == 200
    assert teacher.delete("/api/chat/history").get_json()["suggestions"] == rules.SUGGESTIONS
