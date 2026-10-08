"""Direct answers that must not go through the model (2026-10-04 chat fixes).

Rafael's sessions on Oct 4 showed three misses:
* "Hi" on WhatsApp got a system-health dump (and later the open voice draft) after 12s.
  Greetings get a one-line greeting: no tools, no status.
* "Where are the docs you have completed?" got generic instructions that cited internal spec
  files. It gets the Final Docs link plus his latest finals.
* "Send me last quote" / "status on the last Marley's quote" were treated as new-quote
  dictation ("Missing: client name ... Send was asked and blocked"). A question about an
  existing quote gets the latest matching quote: number, client, total, status, next step.
  Sending it to Rafael himself is a reply, not an outbound send.

Everything here is read-only.
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Optional

# ── greetings ────────────────────────────────────────────────────────────────
_GREET_WORDS = {
    "hi", "hii", "hiii", "hello", "hey", "heya", "hiya", "yo", "sup", "howdy", "hola", "ola", "buenas",
    "gm", "morning", "evening", "afternoon", "good", "buenos", "dias", "días", "tardes", "noches",
    "there", "max", "maxy", "again", "whats", "what's", "up", "how", "are", "you", "u", "doing",
    "it", "going", "rafa", "boss", "ok", "okay", "thanks", "thank", "ty", "bro", "buddy", "que", "tal",
}
_GREET_START = {"hi", "hii", "hiii", "hello", "hey", "heya", "hiya", "yo", "sup", "howdy", "hola", "ola",
                "buenas", "gm", "morning", "evening", "afternoon", "good", "buenos", "whats", "what's", "que"}


def _words(text: str) -> list[str]:
    return re.findall(r"[a-záéíóúñ']+", (text or "").lower())


def is_greeting(text: str) -> bool:
    """'Hi', 'hey Max', 'good evening', 'hola', 'what's up' — nothing else in the message."""
    t = (text or "").strip()
    if not t or len(t) > 40 or re.search(r"\d", t):
        return False
    w = _words(t)
    if not w or len(w) > 5 or w[0] not in _GREET_START:
        return False
    if w[0] == "good" and not (len(w) > 1 and w[1] in {"morning", "afternoon", "evening", "night", "day"}):
        return False
    if w[0] in {"whats", "what's"} and (len(w) < 2 or w[1] != "up"):
        return False
    return all(x in _GREET_WORDS or x in {"night", "day"} for x in w)


def greeting_reply(name: str = "Rafael", now: Optional[datetime] = None) -> str:
    h = (now or datetime.now()).hour
    part = "Good morning" if 5 <= h < 12 else "Good afternoon" if 12 <= h < 18 else "Good evening"
    return f"{part}, {name}. What can I do for you?"


# ── "where are my docs" ──────────────────────────────────────────────────────
_DOC_WORDS = ("docs", "documents", "document", "finals", "files", "pdfs", "paperwork")


def _fuzzy_doc_word(w: str) -> bool:
    if w in _DOC_WORDS or w in {"doc", "final"}:
        return True
    return len(w) >= 4 and any(SequenceMatcher(None, w, d).ratio() >= 0.75 for d in ("docs", "documents", "finals"))


def is_docs_location_request(text: str) -> bool:
    """'Where are the dics you have comoleted?', 'where are my docs', 'where do I find the finals'."""
    t = (text or "").strip().lower()
    if not t or len(t) > 120:
        return False
    if not re.search(r"\b(where(?:'s| is| are| do i| can i)?|wheres|how do i (?:find|see|get to)|link to|show me (?:my|the) )", t):
        return False
    w = _words(t)
    return any(_fuzzy_doc_word(x) for x in w)


def _portal_url() -> str:
    return os.environ.get("EMPIRE_PORTAL_INTERNAL_URL", "http://localhost:3005").rstrip("/")


def public_base() -> str:
    return os.getenv("EMPIRE_PUBLIC_BASE_URL", "https://studio.empirebox.store").rstrip("/")


def latest_final_docs(limit: int = 5) -> list[dict[str, Any]]:
    """Latest final estimate / presentation / invoice / drawing per job (Final Docs groups),
    newest first, real clients only, at most 2 of one type."""
    try:
        import httpx
        r = httpx.get(f"{_portal_url()}/api/v1/docs-hub", params={"group": "1"}, timeout=20.0)
        groups = (r.json() or {}).get("groups") or []
    except Exception:
        return []
    picked: list[dict[str, Any]] = []
    per_type: dict[str, int] = {}
    finals = [g.get("final") for g in groups if isinstance(g, dict) and isinstance(g.get("final"), dict)
              and g.get("type") in ("estimate", "presentation", "invoice", "drawing")]
    finals.sort(key=lambda d: str(d.get("modified") or ""), reverse=True)
    for d in finals:
        who = str(d.get("client") or d.get("designer") or "")
        if not who or re.search(r"mock|sweep|\btest\b|smoke", who + " " + str(d.get("title") or ""), re.I):
            continue
        t = str(d.get("type") or "")
        if per_type.get(t, 0) >= 2:
            continue
        per_type[t] = per_type.get(t, 0) + 1
        picked.append(d)
        if len(picked) >= limit:
            break
    return picked


def docs_location_reply(channel: str = "web") -> str:
    absolute = channel in ("whatsapp", "telegram", "sms", "email")
    base = public_base() if absolute else ""
    link = f"{base}/?screen=final-docs"
    lines = [f"All finished documents are in **Final Docs**: [{'Open Final Docs' if not absolute else link}]({link})"
             if not absolute else f"All finished documents are in Final Docs: {link}"]
    docs = latest_final_docs(5)
    if docs:
        lines.append("")
        lines.append("Latest finals:")
        for d in docs:
            title = d.get("title") or d.get("name") or "Document"
            who = d.get("client") or d.get("designer") or ""
            when = (d.get("modified") or "")[:10]
            href = f"{base}/docs/view?id={d.get('id')}" if d.get("id") else link
            meta = " · ".join(x for x in (who, when) if x)
            if absolute:
                lines.append(f"- {title}{f' ({meta})' if meta else ''}: {href}")
            else:
                lines.append(f"- [{title}]({href}){f' — {meta}' if meta else ''}")
    else:
        lines.append("I couldn't list the latest ones right now; the page above has them all.")
    lines.append("")
    lines.append("Say \"open <client> final estimate\" and I'll open a specific one.")
    return "\n".join(lines)


# ── existing-quote lookup ────────────────────────────────────────────────────
_LOOKUP_CUE = re.compile(
    r"\b(?:status|last|latest|recent|newest|previous|most recent|where (?:is|are|'s)|what(?:'s| is) (?:the )?(?:status|total)|"
    r"send me|send it to me|text me|show me|give me|pull up|resend me|forward me)\b",
    re.I,
)
_QUOTE_WORD = re.compile(r"\b(?:quote|quotes|estimate|estimates|est)\b", re.I)
_CREATE_CUE = re.compile(
    r"\b(?:new|make|create|start|draft|build|prepare|write up|put together)\b[^.?!]{0,40}\b(?:quote|estimate|invoice)\b"
    r"|\b(?:quote|estimate) for\b[^.?!]*\b\d", re.I)
_QUOTE_NUM = re.compile(r"\bEST-\d{4}-\d{2,4}\b", re.I)
_STOP = {
    "can", "could", "would", "will", "you", "please", "send", "me", "like", "a", "an", "the", "voice", "message",
    "note", "status", "on", "of", "for", "last", "latest", "recent", "newest", "previous", "most", "quote",
    "quotes", "estimate", "estimates", "est", "my", "our", "what", "whats", "what's", "is", "it", "to", "and",
    "text", "show", "give", "pull", "up", "resend", "forward", "where", "that", "this", "there", "in", "with",
    "about", "how", "doing", "update", "an", "hey", "hi", "max", "ok", "okay", "so", "just", "get", "total",
    "pdf", "copy", "via", "whatsapp", "here", "now", "one", "job", "client", "customer",
}


def parse_quote_lookup(text: str) -> Optional[dict[str, Any]]:
    """A question about an existing quote, or None. New-quote dictation returns None."""
    t = (text or "").strip()
    if not t or len(t) > 300 or not _QUOTE_WORD.search(t):
        return None
    num = _QUOTE_NUM.search(t)
    if _CREATE_CUE.search(t) and not num:
        return None
    if not (num or _LOOKUP_CUE.search(t)):
        return None
    names = []
    for raw in re.findall(r"[A-Za-z][A-Za-z'’&-]+", t):
        w = re.sub(r"['’]s$", "", raw).strip("'’-").lower()
        if len(w) >= 3 and w not in _STOP:
            names.append(w)
    return {"quote_number": num.group(0).upper() if num else "", "names": names[:3],
            "want_pdf": bool(re.search(r"\b(?:send|pdf|copy|resend|forward)\b", t, re.I))}


_NEXT_STEP = {
    "draft": "It's a draft: review it, then send it to the client when you're ready (nothing has gone out).",
    "pending": "Waiting on your review before it goes to the client.",
    "sent": "Sent to the client: follow up for approval.",
    "viewed": "The client opened it: a good moment to follow up.",
    "approved": "Approved: collect the deposit and schedule the work.",
    "accepted": "Accepted: collect the deposit and schedule the work.",
    "deposit_paid": "Deposit in: schedule production.",
    "rejected": "Declined: ask what would change their mind, or revise.",
    "expired": "Expired: revise the date and resend if the client is still interested.",
}


def find_quote(lookup: dict[str, Any]) -> Optional[dict[str, Any]]:
    from app.services import quote_service as qs
    if lookup.get("quote_number"):
        q = qs.get_quote_by_number(lookup["quote_number"])
        if q:
            return q
    candidates: list[dict[str, Any]] = []
    for name in lookup.get("names") or []:
        rows = (qs.list_quotes(search=name, limit=20) or {}).get("quotes") or []
        if rows:
            candidates = rows
            break
    if not candidates and not lookup.get("names"):
        candidates = (qs.list_quotes(limit=20) or {}).get("quotes") or []
    if not candidates:
        return None
    candidates.sort(key=lambda q: (str(q.get("created_at") or ""), str(q.get("quote_number") or "")), reverse=True)
    return candidates[0]


def _money(v: Any) -> str:
    try:
        return f"${float(v):,.2f}"
    except (TypeError, ValueError):
        return "—"


def quote_status_text(q: dict[str, Any], channel: str = "web") -> str:
    number = q.get("quote_number") or q.get("id")
    status = str(q.get("status") or "draft").lower()
    client = q.get("customer_name") or "—"
    project = q.get("project_name") or ""
    when = str(q.get("created_at") or "")[:10]
    nxt = _NEXT_STEP.get(status, "Open it to see where it stands.")
    absolute = channel in ("whatsapp", "telegram", "sms", "email")
    href = f"{public_base() if absolute else ''}/?screen=quote&id={q.get('id')}"
    head = f"{number} for {client}{f' ({project})' if project else ''}: {_money(q.get('total'))}, status {status}{f', created {when}' if when else ''}."
    link = f"Open: {href}" if absolute else f"[Open {number}]({href})"
    return f"{head}\nNext step: {nxt}\n{link}"


def quote_lookup_reply(text: str, channel: str = "web") -> Optional[dict[str, Any]]:
    lookup = parse_quote_lookup(text)
    if not lookup:
        return None
    try:
        q = find_quote(lookup)
    except Exception:
        return None
    if not q:
        who = " ".join(lookup.get("names") or []) or "that"
        return {"text": f"I couldn't find a quote for {who}. Try the client name or the EST number.", "quote": None, "want_pdf": False}
    return {"text": quote_status_text(q, channel), "quote": q, "want_pdf": lookup["want_pdf"]}


# ── never show internal docs as sources ──────────────────────────────────────
_INTERNAL_SRC = re.compile(
    r"(?:`?(?:docs|backend|app|max|scripts|config|tests)/[\w./-]+`?|\b[\w-]+\.(?:md|py|json|ts|tsx|yaml|yml)\b|"
    r"operating truth registry|surface truth|capability registry|doctrine|system prompt|spec file|CLAUDE\.md|AGENTS\.md)",
    re.I,
)


def scrub_internal_sources(text: str) -> str:
    """Drop source lines that point at internal docs/spec/code files; drop an emptied Sources block."""
    if not text or not _INTERNAL_SRC.search(text):
        return text
    lines = text.split("\n")
    out: list[str] = []
    in_sources = False
    for line in lines:
        s = line.strip()
        if re.match(r"^(?:#{1,6}\s*)?\**sources?\**:?\s*$", s, re.I):
            in_sources = True
            out.append(line)
            continue
        if in_sources and s and not re.match(r"^(?:\d+[.)]|[-*•])\s", s):
            in_sources = False
        if in_sources and _INTERNAL_SRC.search(s) and not re.search(r"https?://", s):
            continue
        out.append(line)
    # remove a Sources heading with nothing under it
    cleaned: list[str] = []
    for i, line in enumerate(out):
        if re.match(r"^(?:#{1,6}\s*)?\**sources?\**:?\s*$", line.strip(), re.I):
            rest = [x for x in out[i + 1:] if x.strip()]
            if not rest or not re.match(r"^(?:\d+[.)]|[-*•])\s", rest[0].strip()):
                continue
        cleaned.append(line)
    result = "\n".join(cleaned)
    # inline mentions like "(see docs/MAX_DOCUMENT_WORKSPACE.md)"
    result = re.sub(r"\s*\((?:see |per |from )?`?(?:docs|backend|max)/[\w./-]+\.md`?[^)]*\)", "", result)
    return re.sub(r"\n{3,}", "\n\n", result).strip()


# ── router hook ──────────────────────────────────────────────────────────────
def direct_reply(message: str, *, channel: str = "web", has_image: bool = False) -> Optional[dict[str, Any]]:
    """Return {'text', 'skill', 'quote'?} for messages answered without the model, else None."""
    if has_image:
        return None  # the model must read the attached image first
    if is_greeting(message):
        return {"text": greeting_reply(), "skill": "greeting"}
    if is_docs_location_request(message):
        return {"text": docs_location_reply(channel), "skill": "docs_location"}
    try:  # 2026-10-06 model first: only an exact EST number is answered here; names go to the model + search_quotes
        from app.services.max import answer_policy
        if answer_policy.model_first() and not answer_policy.is_exact_quote_lookup(message):
            return None
    except Exception:
        pass
    found = quote_lookup_reply(message, channel)
    if found:
        return {"text": found["text"], "skill": "quote_lookup", "quote": found.get("quote"), "want_pdf": found.get("want_pdf")}
    return None
