"""The one call to the outside AI service for the navigation chatbot. Tests replace ask_model()."""

import json
import os
import urllib.request

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 100
TIMEOUT_SECONDS = 10


def ask_model(message, pages, prompt):
    """The page key the model picked for this question, or None if there is no API key, the call
    failed, or the model did not pick a page. Only the question and the page list are sent: no names,
    classes, scores or earlier messages. Never raises, so the chat just says it is not available."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    body = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": prompt,
        "messages": [{"role": "user", "content": message}],
        "tools": [{
            "name": "navigate",
            "description": "Open one page of MyGuro for the teacher.",
            "input_schema": {"type": "object", "required": ["page"],
                             "properties": {"page": {"type": "string", "enum": [*pages, "none"]}}},
        }],
        "tool_choice": {"type": "tool", "name": "navigate"},  # it must pick a page, it cannot just talk
    }
    request = urllib.request.Request(
        API_URL, data=json.dumps(body).encode(), method="POST",
        headers={"content-type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            data = json.load(response)
        for block in data["content"]:
            if block.get("type") == "tool_use" and block.get("name") == "navigate":
                return block["input"].get("page")
    except Exception:  # any failure (network, key, limit, odd answer) means "not available"
        return None
    return None
