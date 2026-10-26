"""The one call to the outside AI service (Google Gemini) for the navigation chatbot. Tests replace ask_model()."""

import json
import os
import urllib.request

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
# Models change often: the server can set another one with GEMINI_MODEL without a code change.
DEFAULT_MODEL = "gemini-2.5-flash-lite"
MAX_TOKENS = 60
TIMEOUT_SECONDS = 10


def ask_model(message, topics, prompt):
    """The topic key (a page or a how-to) the model picked for this question, or None if there is no API
    key, the call failed, or the model did not pick one. Only the question and the topic list are sent: no names,
    classes, scores or earlier messages. Never raises, so the chat just says it is not available."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    body = {
        "systemInstruction": {"parts": [{"text": prompt}]},
        "contents": [{"role": "user", "parts": [{"text": message}]}],
        "tools": [{"functionDeclarations": [{
            "name": "help",
            "description": "Show the teacher a page of MyGuro or a how-to guide.",
            "parameters": {"type": "OBJECT", "required": ["key"],
                           "properties": {"key": {"type": "STRING", "enum": [*topics, "none"]}}},
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
    except Exception:  # any failure (network, key, limit, odd answer) means "not available"
        return None
    return None
