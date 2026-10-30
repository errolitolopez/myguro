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
