"""Every English sentence in the pages that are translated has a Taglish entry, with the same {placeholders}."""

import re

import pytest

from myguro.i18n.tl import TAGLISH

# The files whose text is translated so far. Each translating task adds its files here.
TRANSLATED_FILES = [
    # Shared and sign-in pages
    "myguro/templates/_navbar.html", "myguro/templates/base.html", "myguro/templates/_language_select.html",
    "myguro/templates/_theme_select.html", "myguro/templates/login.html", "myguro/templates/forgot_password.html",
    "myguro/templates/change_password.html", "myguro/templates/recovery_code.html",
    "myguro/static/js/login.js", "myguro/static/js/forgot-password.js", "myguro/static/js/change-password.js",
    "myguro/static/js/recovery-code.js", "myguro/static/js/password-toggle.js", "myguro/static/js/palette.js",
    "myguro/static/js/common.js",
    # Student dashboard
    "myguro/templates/dashboard.html", "myguro/templates/_dashboard_chart.html",
    "myguro/static/js/student-widgets.js", "myguro/static/js/dashboard-chart.js", "myguro/static/js/tips.js",
    # My activities
    "myguro/templates/my_activities.html", "myguro/static/js/my-activities.js",
    # The answer page
    "myguro/templates/answer.html", "myguro/static/js/answer.js",
    # Feedback and Display
    "myguro/templates/feedback.html", "myguro/static/js/feedback.js", "myguro/templates/display.html",
    "myguro/templates/_reading_settings.html",
    # The error page (its title and message come from errors.py and are translated there)
    "myguro/templates/error.html",
]

PLACEHOLDER = re.compile(r"\{(\w+)\}")
QUOTED = r'"((?:[^"\\]|\\.)*)"'
TEMPLATE_CALL = re.compile(r"\b_\(\s*" + QUOTED)  # _("To do") in a template
SCRIPT_CALL = re.compile(r"\bt\(\s*" + QUOTED)  # t("To do") in JavaScript


def english_sentences(text, pattern):
    """The English sentences a file asks for, with the backslash escapes of the quotes taken out."""
    return {match.replace('\\"', '"').replace("\\\\", "\\") for match in pattern.findall(text)}


def sentences_of(path):
    pattern = SCRIPT_CALL if path.endswith(".js") else TEMPLATE_CALL
    return english_sentences(open(path).read(), pattern)


def test_the_helper_reads_a_sentence_with_an_escaped_quote():
    assert english_sentences('_("He said \\"hi\\"") _("To do")', TEMPLATE_CALL) == {'He said "hi"', "To do"}
    assert english_sentences("t(\"You're all caught up.\", {})", SCRIPT_CALL) == {"You're all caught up."}


@pytest.mark.parametrize("path", TRANSLATED_FILES)
def test_every_sentence_has_a_taglish_entry(path):
    missing = sorted(sentence for sentence in sentences_of(path) if sentence not in TAGLISH)
    assert not missing, f"{path} has no Taglish for: {missing}"


def test_taglish_keeps_the_same_placeholders():
    for english, taglish in TAGLISH.items():
        assert set(PLACEHOLDER.findall(english)) == set(PLACEHOLDER.findall(taglish)), english


def test_no_sentence_is_wrapped_twice():
    # A template sentence wrapped inside another (_("{{ _("To do") }}")) draws as broken text and fails the page.
    for path in [p for p in TRANSLATED_FILES if p.endswith(".html")]:
        assert '_("{{' not in open(path).read(), path


def test_every_feedback_question_has_a_taglish_entry():
    # The questions live on the server (domain/feedback.py), so the regex over the pages cannot see them.
    from myguro.domain.feedback import QUESTIONS

    missing = [text for _, text in QUESTIONS if text not in TAGLISH]
    assert not missing, f"no Taglish for the feedback questions: {missing}"
