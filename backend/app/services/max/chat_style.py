"""Chat reply style + Chief e awareness for Max (2026-10-04).

Appended to get_system_prompt(). Two parts:

* Reply style (all editions): lead with the answer, keep it short, sources as a
  compact numbered list (the studio folds that list into "Sources (n)"), and
  check the user's own records first when they refer to their house, bills, a
  claim, a client or a job.
* Chief e (Rafael's main edition only): Chief e is Rafael's Grok Bot assistant.
  Max never says it does not exist; it offers the [Ask Chief e](chief-e:ask)
  link, which the studio turns into a button that opens Grok Bot with the
  question pre-filled. Family editions (AMP / Max-e, Maxine) never see this.
"""
from __future__ import annotations

import os

FAMILY_MARKERS = ("/data/amp", "/data/maxine", "empire-amp", "empire-maxine")

REPLY_STYLE = """

=== CHAT REPLY FORMAT (default for every chat reply) ===
- Lead with the direct answer in 1-2 sentences. Then at most 3-5 short bullets of what matters for the user.
- Aim for under ~180 words before sources. Go longer only when the user asks for detail, a report, a plan or a comparison table.
- Use markdown sparingly: short `###` headings only when there are 2+ distinct parts; bullets, not walls of text.
- Cite with numbered inline links like [1](https://example.com). List sources once at the end under `Sources` as one line each: `1. Title — site (date)`. Never paste raw URLs in the body.
- One reply answers one message. Do not restate earlier answers.
- Own records first: when the user says "this house", "my house", "my bills", "my electric bill", a claim (for example an insurance claim), a client, a job or a quote, check their own data first (claims, bills, documents, jobs, quotes, customers, memory) and answer from it. Use web research only for the general part, and say which part came from their records.
- If a key fact is missing (address, bill amounts, system size), ask one short question instead of guessing.
"""

CHIEF_E = """

=== CHIEF E (Rafael's Grok Bot assistant) ===
- Chief e is Rafael's personal Grok Bot assistant. It is a separate agent, not a model in your routing, and it works across his businesses, computers and accounts. It reviews your daily session exports.
- You cannot read Chief e's memory or chats. Never say Chief e or Grok Bot "doesn't exist" or "isn't in this stack".
- When Rafael asks about Grok Bot / Chief e, asks what Chief e knows, or asks for something Chief e handles better (work on his computers or accounts, cross-business follow-ups), say so in one line and offer exactly this link: [Ask Chief e](chief-e:ask) — the studio turns it into a button that opens Grok Bot with his question.
- The studio header also has an "Ask Chief e" button.
"""


def _is_family() -> bool:
    edition = (os.getenv("EMPIRE_EDITION") or "").strip().lower()
    if edition not in ("", "main", "workroom"):
        return True
    paths = " ".join(os.getenv(k, "") for k in ("EMPIRE_DATA_DIR", "DATABASE_URL", "MAX_MEMORY_PATH"))
    return any(m in paths for m in FAMILY_MARKERS) or any(m in os.getcwd() for m in FAMILY_MARKERS)


def render_chat_style_section() -> str:
    return REPLY_STYLE + ("" if _is_family() else CHIEF_E)
