"""Cleaning the formatted (bold, italic, lists) text of a section description.

The editor posts HTML. Only the tags in ALLOWED_TAGS are kept, without attributes; every
other tag is dropped (its text stays), and script/style are dropped with their content.
What is stored is safe to show with innerHTML.
"""

from html import escape
from html.parser import HTMLParser

ALLOWED_TAGS = {"p", "div", "br", "b", "strong", "i", "em", "u", "ul", "ol", "li"}
VOID_TAGS = {"br"}
DROPPED_WITH_CONTENT = {"script", "style", "template", "iframe", "object", "noscript"}
MAX_HTML_LENGTH = 100000  # parsed before the length rule, so very large posts are refused early


class _Cleaner(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.open_tags = []
        self.skipping = 0
        self.text = []

    def handle_starttag(self, tag, attrs):
        if tag in DROPPED_WITH_CONTENT:
            self.skipping += 1
        elif tag in ALLOWED_TAGS and not self.skipping:
            self.parts.append(f"<{tag}>")
            if tag not in VOID_TAGS:
                self.open_tags.append(tag)

    def handle_startendtag(self, tag, attrs):
        if tag in VOID_TAGS and not self.skipping:
            self.parts.append(f"<{tag}>")

    def handle_endtag(self, tag):
        if tag in DROPPED_WITH_CONTENT:
            self.skipping = max(0, self.skipping - 1)
        elif tag in self.open_tags and not self.skipping:
            while self.open_tags:  # close anything left open inside it
                last = self.open_tags.pop()
                self.parts.append(f"</{last}>")
                if last == tag:
                    break

    def handle_data(self, data):
        if not self.skipping:
            self.parts.append(escape(data, quote=False))
            self.text.append(data)

    def result(self):
        while self.open_tags:
            self.parts.append(f"</{self.open_tags.pop()}>")
        return "".join(self.parts), "".join(self.text)


def clean_rich_text(value):
    """Posted HTML -> safe HTML; "" when it has no text (an empty editor posts "<br>")."""
    cleaner = _Cleaner()
    cleaner.feed(str(value or "")[:MAX_HTML_LENGTH])
    cleaner.close()
    html, text = cleaner.result()
    return html.strip() if text.strip() else ""


def rich_text_length(html):
    """Number of typed characters (tags not counted)."""
    cleaner = _Cleaner()
    cleaner.feed(html)
    cleaner.close()
    return len(cleaner.result()[1])
