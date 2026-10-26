"""The one call to the outside AI service (Google Gemini) for the navigation chatbot. Tests replace ask_model()."""

import json
import os
import shlex
import urllib.request

from flask import current_app

from myguro.domain.chat import SPECIAL_KEYS

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
# Models change often: the server can set another one with GEMINI_MODEL without a code change.
DEFAULT_MODEL = "gemini-2.5-flash-lite"
MAX_TOKENS = 60
TIMEOUT_SECONDS = 10


def find_api_key():
    """The Gemini key: the GEMINI_API_KEY environment variable, else the line `export GEMINI_API_KEY=...`
    in instance/gemini.env (saved by set-gemini-key.sh). The file is read here because a server that
    does not start the app with run.sh (PythonAnywhere) never reads the environment of that script."""
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    try:
        with open(os.path.join(current_app.instance_path, "gemini.env")) as saved:
            for line in saved:
                words = shlex.split(line)  # the script quotes the key, so split it the way a shell would
                if len(words) == 2 and words[0] == "export" and words[1].startswith("GEMINI_API_KEY="):
                    return words[1].split("=", 1)[1] or None
    except (OSError, ValueError):
        pass
    return None


def ask_model(message, topics, prompt, history=()):
    """The topic key (a page or a how-to) the model picked for this question, or None if there is no API
    key, the call failed, or the model did not pick one. Only the question and the topic list are sent: no names,
    classes or scores, and only the latest few earlier messages of this teacher (history: [(sender, text)]). Never raises, so the chat just says it is not available."""
    api_key = find_api_key()
    if not api_key:
        current_app.logger.warning("GuroBot: no Gemini API key (set GEMINI_API_KEY or run set-gemini-key.sh).")
        return None
    body = {
        "systemInstruction": {"parts": [{"text": prompt}]},
        "contents": [
            *[{"role": "user" if sender == "teacher" else "model", "parts": [{"text": text}]} for sender, text in history],
            {"role": "user", "parts": [{"text": message}]},
        ],
        "tools": [{"functionDeclarations": [{
            "name": "help",
            "description": "Show the teacher a page of MyGuro or a how-to guide.",
            "parameters": {"type": "OBJECT", "required": ["key"],
                           "properties": {"key": {"type": "STRING", "enum": [*topics, *SPECIAL_KEYS]}}},
        }]}],
        # It must call help, it cannot just talk
        "toolConfig": {"functionCallingConfig": {"mode": "ANY", "allowedFunctionNames": ["help"]}},
        "generationConfig": {"maxOutputTokens": MAX_TOKENS, "temperature": 0},
    }
    request = urllib.request.Request(
        API_URL.format(model=os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL),
        data=json.dumps(body).encode(), method="POST",
        headers={"content-type": "application/json", "x-goog-api-key": api_key})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            data = json.load(response)
        for part in data["candidates"][0]["content"]["parts"]:
            call = part.get("functionCall")
            if call and call.get("name") == "help":
                return call["args"].get("key")
    except Exception as error:  # any failure (network, key, limit, odd answer) means "not available"
        # The reason goes to the server log only (never the key, which is in a header), so it can be fixed
        current_app.logger.warning("GuroBot: the Gemini call failed: %s: %s", type(error).__name__, error)
        return None
    current_app.logger.warning("GuroBot: Gemini did not pick a topic.")
    return None
