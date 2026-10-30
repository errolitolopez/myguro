"""The language setting: the cookie, the Taglish dictionary, and the text helpers."""

from myguro.domain.i18n import DEFAULT_LANGUAGE, LANGUAGES, language_from_cookie, translate


def test_language_comes_from_the_cookie_and_defaults_to_english():
    assert LANGUAGES == ("en", "tl") and DEFAULT_LANGUAGE == "en"
    assert language_from_cookie("tl") == "tl"
    for value in (None, "", "TL", "fil", "en", "tl ", "<script>"):
        assert language_from_cookie(value) == "en"


def test_translate_uses_the_dictionary_and_falls_back_to_english():
    assert translate("To do", {"To do": "Gagawin"}) == "Gagawin"
    assert translate("To do", {}) == "To do"  # no entry: the English sentence, never an error


def test_translate_fills_placeholders():
    assert translate("{n} done", {"{n} done": "{n} tapos na"}, {"n": 3}) == "3 tapos na"
    assert translate("{n} done", {}, {"n": 3}) == "3 done"
    assert translate("Hi {name}", {}, {}) == "Hi {name}"  # no value: left as written
    assert translate("A {literal} and { }", {}, None) == "A {literal} and { }"


# --- Flask: _() in templates, window.TEXT, t() in JavaScript ---------------------------

from flask import render_template, render_template_string  # noqa: E402

from app import app as flask_app  # noqa: E402
from myguro.i18n.tl import TAGLISH  # noqa: E402


def render(source, cookie=None, **values):
    headers = {"Cookie": f"myguro-lang={cookie}"} if cookie is not None else {}
    with flask_app.test_request_context("/login", headers=headers):
        return render_template_string(source, **values)


def test_template_text_follows_the_language_cookie(monkeypatch):
    monkeypatch.setitem(TAGLISH, "Display", "Itsura")
    assert render('{{ _("Display") }}', cookie="tl") == "Itsura"
    assert render('{{ _("Display") }}', cookie="en") == "Display"
    assert render('{{ _("Display") }}') == "Display"  # no cookie: English
    assert render('{{ _("Display") }}', cookie="nonsense") == "Display"
    assert render('{{ LANG }}', cookie="tl") == "tl" and render('{{ LANG }}') == "en"


def test_template_text_fills_placeholders(monkeypatch):
    monkeypatch.setitem(TAGLISH, "{count} to do", "{count} pa ang gagawin")
    assert render('{{ _("{count} to do", count=3) }}', cookie="tl") == "3 pa ang gagawin"
    assert render('{{ _("{count} to do", count=3) }}') == "3 to do"


def test_the_page_carries_the_dictionary_only_in_taglish(monkeypatch):
    monkeypatch.setitem(TAGLISH, "Display", "Itsura")
    monkeypatch.setitem(TAGLISH, "Bad", "</script><b>x")
    with flask_app.test_request_context("/login", headers={"Cookie": "myguro-lang=tl"}):
        page = render_template("login.html")
    assert '"Display": "Itsura"' in page
    assert "</script><b>x" not in page  # a closing tag inside a string must not end the script
    with flask_app.test_request_context("/login"):
        assert "window.TEXT = {}" in render_template("login.html")


def test_javascript_has_the_same_text_helper():
    script = open("myguro/static/js/common.js").read()
    assert "function t(" in script and "window.TEXT" in script
