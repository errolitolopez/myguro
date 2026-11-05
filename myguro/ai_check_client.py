"""The call to the outside AI service (Google Gemini) for "Check with AI". Tests replace ask_model()."""

import json
import os
import urllib.request

from flask import current_app

from myguro.chat_client import API_URL, DEFAULT_MODEL, TIMEOUT_SECONDS, find_api_key
from myguro.domain.ai_check import SYSTEM_PROMPT

MAX_TOKENS = 400


def ask_model(text):
    """The model's reply {points, explanation} for one answer (see domain/ai_check.build_request), or None when
    there is no API key, the call failed or the reply was not JSON. Never raises, so the page just says the
    check is not available."""
    api_key = find_api_key()
    if not api_key:
        current_app.logger.warning("AI check: no Gemini API key (set GEMINI_API_KEY or run set-gemini-key.sh).")
        return None
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": text}]}],
        "generationConfig": {
            "maxOutputTokens": MAX_TOKENS, "temperature": 0.2,
            # The reply must be JSON of this shape, so it can be read without guessing
            "responseMimeType": "application/json",
            "responseSchema": {"type": "OBJECT", "required": ["points", "explanation"], "properties": {
                "points": {"type": "INTEGER"}, "explanation": {"type": "STRING"}}},
        },
    }
    request = urllib.request.Request(
        API_URL.format(model=os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL),
        data=json.dumps(body).encode(), method="POST",
        headers={"content-type": "application/json", "x-goog-api-key": api_key})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            data = json.load(response)
        return json.loads(data["candidates"][0]["content"]["parts"][0]["text"])
    except Exception as error:  # any failure (network, key, limit, odd answer) means "not available"
        # The reason goes to the server log only (never the key, which is in a header or the answer)
        current_app.logger.warning("AI check: the Gemini call failed: %s: %s", type(error).__name__, error)
        return None
