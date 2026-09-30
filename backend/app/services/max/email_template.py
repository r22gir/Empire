"""House email rendering for MAX and Empire email services.

The renderer deliberately produces both RFC multipart alternatives from one
plain-text source. This keeps line breaks readable in clients that prefer the
plain part while giving HTML-capable clients a branded, structured layout.
"""
from __future__ import annotations

from dataclasses import dataclass
from html import escape
from html.parser import HTMLParser
import re


SIGNATURE_LINES = (
    "Empire Workroom",
    "Rafael Giraldo",
    "workroom@empirebox.store",
    "+1 703-213-6484",
)

_AMOUNT_RE = re.compile(
    r"^(?P<label>[^:]+):\s*(?P<amount>[$€£]\s?[-\d,]+(?:\.\d{2})?)\s*$"
)


@dataclass(frozen=True)
class RenderedEmail:
    plain_text: str
    html: str


class _HTMLToText(HTMLParser):
    """Small, dependency-free HTML-to-text converter for legacy callers."""

    _BLOCK_TAGS = {"br", "p", "div", "li", "tr", "h1", "h2", "h3", "hr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag.lower() in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def html_to_text(value: str) -> str:
    """Convert legacy HTML bodies to readable plain text before rendering."""
    parser = _HTMLToText()
    parser.feed(value or "")
    parser.close()
    lines = [line.strip() for line in "".join(parser.parts).splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _plain_with_signature(body_text: str) -> str:
    body = body_text.replace("\r\n", "\n").replace("\r", "\n").strip()
    signature = "\n".join(SIGNATURE_LINES)
    if body.endswith(signature):
        return body
    return f"{body}\n\n{signature}"


def _is_amount(line: str) -> bool:
    return bool(_AMOUNT_RE.match(line.strip()))


def _amount_table(lines: list[str]) -> str:
    rows = []
    for line in lines:
        match = _AMOUNT_RE.match(line.strip())
        if not match:
            continue
        rows.append(
            "<tr><th scope=\"row\">{label}</th><td>{amount}</td></tr>".format(
                label=escape(match.group("label").strip(), quote=False),
                amount=escape(match.group("amount").strip(), quote=False),
            )
        )
    return "<table class=\"amounts\"><tbody>" + "".join(rows) + "</tbody></table>"


def _body_to_html(body_text: str) -> str:
    """Render paragraphs, bullet lists, and currency lines structurally."""
    lines = body_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks: list[list[str]] = []
    current: list[str] = []
    for raw in lines:
        line = raw.strip()
        if line:
            current.append(line)
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)

    rendered: list[str] = []
    for block in blocks:
        i = 0
        while i < len(block):
            line = block[i]
            if line.startswith("- "):
                bullets: list[str] = []
                while i < len(block) and block[i].startswith("- "):
                    bullets.append(f"<li>{escape(block[i][2:].strip(), quote=False)}</li>")
                    i += 1
                rendered.append("<ul>" + "".join(bullets) + "</ul>")
                continue
            if _is_amount(line):
                amounts: list[str] = []
                while i < len(block) and _is_amount(block[i]):
                    amounts.append(block[i])
                    i += 1
                rendered.append(_amount_table(amounts))
                continue
            rendered.append(f"<p>{escape(line, quote=False)}</p>")
            i += 1

    return "\n".join(rendered)


def render_house_email(body_text: str) -> RenderedEmail:
    """Return the house plain-text and branded HTML email alternatives."""
    plain = _plain_with_signature(body_text)
    body_html = _body_to_html(body_text)
    signature_html = (
        '<div class="signature"><strong>Empire Workroom</strong>'
        "<br>Rafael Giraldo"
        "<br><a href=\"mailto:workroom@empirebox.store\">workroom@empirebox.store</a>"
        "<br>+1 703-213-6484</div>"
    )
    html = f"""<!doctype html>
<html><body style="margin:0;background:#f7f5f0;color:#252525;font-family:Arial,Helvetica,sans-serif;line-height:1.5">
  <div style="max-width:680px;margin:0 auto;padding:32px 28px;background:#fff">
    <div style="border-top:4px solid #b08d35;padding-top:20px">
      <div class="email-body">{body_html}</div>
      {signature_html}
    </div>
  </div>
</body></html>"""
    return RenderedEmail(plain_text=plain, html=html)
