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

    def fake(message, pages, prompt):
        Fake.calls.append((message, list(pages), prompt))
        return Fake.key

    Fake.calls = []
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
        asked.key = key
        assert say(teacher).get_json()["link"]["url"] == path
        assert teacher.get(path).status_code == 200, path


@pytest.mark.parametrize("picked", ["none", "../admin", "/users", "https://example.com", "", 5])
def test_unknown_key_or_no_page_gets_the_fixed_reply(teacher, chat_on, asked, picked):
    asked.key = picked
    assert say(teacher).get_json() == {"reply": rules.NO_PAGE_REPLY, "link": None}


def test_service_not_available_gets_a_plain_reply(teacher, chat_on, asked):
    asked.key = None
    assert say(teacher).get_json() == {"reply": rules.UNAVAILABLE_REPLY, "link": None}


def test_no_api_key_means_not_available(teacher, chat_on, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert say(teacher).get_json()["link"] is None


def test_only_the_question_and_the_page_list_are_sent(teacher, chat_on, asked):
    say(teacher, "  where   are my classes? ")
    (message, keys, prompt), = asked.calls
    assert message == "where are my classes?"
    assert keys == list(rules.TEACHER_PAGES)
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


def test_messages_are_not_stored(teacher, chat_on, asked, app):
    say(teacher, "secretword please")
    import sqlite3, os
    connection = sqlite3.connect(os.environ["MYGURO_DATABASE"])
    dump = "\n".join(connection.iterdump())
    connection.close()
    assert "secretword" not in dump



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
    """The real client with the network replaced: forced navigate call, key in a header, page read back."""
    import io, json, urllib.request
    seen = {}

    def fake_urlopen(request, timeout):
        seen["body"] = json.loads(request.data)
        seen["key"] = request.get_header("X-goog-api-key")
        reply = {"candidates": [{"content": {"parts": [{"functionCall": {"name": "navigate", "args": {"page": "classes"}}}]}}]}
        return io.BytesIO(json.dumps(reply).encode())

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert chat_client.ask_model("my classes", rules.TEACHER_PAGES, "prompt") == "classes"
    assert seen["key"] == "test-key"
    assert seen["body"]["toolConfig"]["functionCallingConfig"]["allowedFunctionNames"] == ["navigate"]
    assert seen["body"]["contents"][0]["parts"][0]["text"] == "my classes"
    assert seen["body"]["tools"][0]["functionDeclarations"][0]["parameters"]["properties"]["page"]["enum"][-1] == "none"
