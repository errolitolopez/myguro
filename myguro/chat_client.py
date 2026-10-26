"""The one call to the outside AI service (Google Gemini) for the navigation chatbot. Tests replace ask_model()."""

import json
import os
import urllib.request

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
# Models change often: the server can set another one with GEMINI_MODEL without a code change.
DEFAULT_MODEL = "gemini-2.5-flash-lite"
MAX_TOKENS = 100
TIMEOUT_SECONDS = 10


def ask_model(message, pages, prompt):
    """The page key the model picked for this question, or None if there is no API key, the call
    failed, or the model did not pick a page. Only the question and the page list are sent: no names,
    classes, scores or earlier messages. Never raises, so the chat just says it is not available."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    body = {
        "systemInstruction": {"parts": [{"text": prompt}]},
        "contents": [{"role": "user", "parts": [{"text": message}]}],
        "tools": [{"functionDeclarations": [{
            "name": "navigate",
            "description": "Open one page of MyGuro for the teacher.",
            "parameters": {"type": "OBJECT", "required": ["page"],
                           "properties": {"page": {"type": "STRING", "enum": [*pages, "none"]}}},
        }]}],
        # It must call navigate, it cannot just talk
        "toolConfig": {"functionCallingConfig": {"mode": "ANY", "allowedFunctionNames": ["navigate"]}},
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
            if call and call.get("name") == "navigate":
                return call["args"].get("page")
    except Exception:  # any failure (network, key, limit, odd answer) means "not available"
        return None
    return None
