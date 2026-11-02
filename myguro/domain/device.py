"""Turns a browser's User-Agent text into a short device name for the sign-in log. No database, no Flask."""

MAX_DEVICE_LENGTH = 60  # the log keeps a short name, never the raw (long, fingerprint-like) User-Agent text

# Checked in this order: many browsers also say "Chrome" or "Safari" in their text, so the specific
# ones (Edge, Opera, Samsung Internet, Firefox) must come before Chrome, and Chrome before Safari.
BROWSERS = (("Edg/", "Edge"), ("EdgA/", "Edge"), ("EdgiOS/", "Edge"), ("OPR/", "Opera"),
            ("SamsungBrowser/", "Samsung Internet"), ("Firefox/", "Firefox"), ("FxiOS/", "Firefox"),
            ("CriOS/", "Chrome"), ("Chrome/", "Chrome"), ("Safari/", "Safari"))

# Checked in this order too: an iPhone's text also says "like Mac OS X", and Android's says "Linux".
SYSTEMS = (("iPhone", "iPhone"), ("iPad", "iPad"), ("Android", "Android"), ("Windows", "Windows"),
           ("CrOS", "ChromeOS"), ("Macintosh", "Mac"), ("Linux", "Linux"))


def device_name(user_agent):
    """"Chrome on Windows", "Safari on iPhone"... or "" when the browser sent nothing, or just the part
    that is known ("Chrome", "Android"). Short on purpose: the raw text is never stored."""
    text = str(user_agent or "")
    browser = next((name for mark, name in BROWSERS if mark in text), "")
    system = next((name for mark, name in SYSTEMS if mark in text), "")
    if browser and system:
        return f"{browser} on {system}"[:MAX_DEVICE_LENGTH]
    return (browser or system)[:MAX_DEVICE_LENGTH]
