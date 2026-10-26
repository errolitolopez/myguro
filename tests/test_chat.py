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
