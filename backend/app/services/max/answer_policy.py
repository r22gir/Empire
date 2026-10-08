"""Max answer policy: model first, few shortcuts, plain replies (2026-10-06).

Rafael approved this simplification after a week of poor answers caused by a
stack of shortcuts, routers and guards that grabbed messages before the model
saw them (a 'what's new' changelog for a solar/Travelers question, web research
for 'what are you building', raw guard text such as "Claim 'I read' has no
structured proof object", email refusals).

Default path now: the model, with the system prompt (Rafael's rules), the Chief e
brief, Max's memory and the tools. Only intercepts that are fast AND correct stay
in front of it (KEPT_SHORTCUTS). The rest are demoted to tools the model chooses
(DEMOTED says which). Internal guard/template text never reaches Rafael
(clean_reply). Hard limits are unchanged and live where they always did:
  * sends to anyone but Rafael's own addresses: recipient allowlist in the send
    tools + approval queue (tool_executor / email_recipient_whitelist),
  * destructive tools: founder PIN gate in tool_executor,
  * input guardrails, GPU safety lock, family isolation, tests on copies.

Set MAX_MODEL_FIRST=0 to restore the old routing without a code change.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Iterable, Optional

logger = logging.getLogger("max.answer_policy")

# Intercepts that stay in front of the model: fast, deterministic, correct.
KEPT_SHORTCUTS = frozenset({
    "input_guard",          # check_input / sanitizer refusals (safety)
    "gpu_guard",            # EmpireDell GPU stability lock (safety)
    "greeting",             # "hi" -> one line, no tools
    "docs_location",        # "where are my docs" -> Final Docs link + latest finals
    "exact_quote_number",   # "status of EST-2026-297" -> number, client, total, status
    "attachment_missing",   # upload never arrived -> plain sentence (no model guess)
    "drawing",              # drawing router (shop drawings have their own engine)
    "link_intelligence",    # a pasted URL -> link brief
    "continuity",           # explicit continuity commands
    "provider_identity", "openclaw_gate", "hermes", "archiveforge", "vendorops",
    "inventory_clarify",
})

# Former intercepts and where that job lives now.
DEMOTED = {
    "self_status": "max_status tool",
    "whats_new": "model (max_status / git context)",
    "runtime_truth": "empire_runtime_truth_check / get_services_health tools",
    "quote_lookup_by_name": "search_quotes / get_quote tools",
    "module_knowledge": "model with system prompt",
    "live_lookup": "web_search (pre-search only for research/news asks)",
    "gmail_inbox": "check_email tool",
    "email_send_boundary": "send_email tool (recipient allowlist enforced in the tool)",
    "email_reply_boundary": "check_email tool",
    "voice_status": "model (voice capability in context)",
    "founder_status_block": "removed (steps stay in the UI 'done' event)",
    "truth_guard_canned_reply": "unsupported sentences are dropped, the rest of the answer stays",
}

ATTACHMENT_MISSING_TEXT = ("I didn't get the image. It never finished uploading on my side. "
                           "Try attaching it again.")
UNCONFIRMED_TEXT = "I don't have a confirmed result for that yet. Want me to check it now?"

STYLE_DIRECTIVE = """

## How to answer (Rafael, 2026-10-06; this overrides older format rules)
- Answer like a good assistant who knows his business: short and plain. Lead with the answer in one to three sentences; add a few bullets only when there are several items.
- No markdown headers, no "Verified" / "Max's inference" labels, no "Status / Done / Not done" blocks, no Sources section, unless he asked for research. Never paste tool output, guard messages or internal notes.
- Ground every fact in a tool result or the context above (Chief e brief, memory, live state). If you did not look it up, look it up with a tool first; if a lookup fails, say so in one sentence.
- Pick the tool yourself: search_quotes / get_quote for quotes (aliases: Dahlia = Dahlia Design = Nehal Elrefai; Philipp / Phillip / Naomi wall unit = Lauren Bassett / LB Design job), find_files for documents, PDFs, mockups and job visuals (never Unsplash for a live job), max_status for "what are you building / what's next / status", check_email for his inbox, get_services_health for "are you working", request_improvement when he asks to change or fix Empire, web_search only for public facts or when he asks for research, search_images only when he asks for public/stock inspiration.
- Email only when he asks you to send, email or forward something. "Find / show / look up / pull up / what's" is answered here in the chat (in Studio, share_file with via="studio" gives a link); never email it, just offer to.
- When he does ask to send to himself (his own email, this chat, his WhatsApp), that is a reply: do it right away with send_quote_email / send_email / share_file, no PIN, no second yes. Anyone else needs his explicit yes first; draft and ask.
- Use his context: the Travelers claim is the house at 44 Burns St NE (claim JJN4296); Nelma's Workroom bills some jobs.
- Reply in the language he wrote in (Spanish or English).
- Short never means dropping facts: keep the client name, quote numbers (EST-...), totals and file names you looked up. Lists are plain "- " bullets.
- Voice-message or quick status asks: under 70 words (quote number, client, total, status, next step).
- "Brief me / today / rundown / what's on my plate": one "- " line per active job from the Chief e brief (Marley's, Dahlia/Nehal, Philipp/Naomi, Willard, the Travelers claim, ...) with its next step, then what waits on his tap. Under 150 words.
- Job visuals (mockup, drawing, diagram, picture, layout; typos like "mick up drwings"): run find_files, name the actual file and its folder, and share it with share_file (via="studio" link in Studio, this chat on WhatsApp; email only if he asked to email it). Never describe the design in words instead of the file.
- Weather: call get_weather (Empire Workroom is in Hyattsville, MD).
- Measurements are always fractions of an inch, never decimals (26 3/4", not 26.75"). Channel cuts add 2 1/2" for board and foam, so a 12" channel is cut at least 18".
- Upholstery estimates: group lines by area (U banquette, L banquette, material) with room=area, sq_ft and price_per_sqft per piece, measurements on the second description line in fractions; subtotal per area, then grand total, deposit, balance.
- One quote per ask: never create a companion, split or alternate quote he did not ask for (offer it in one line instead). When he says go to a plan, run its tools in that same reply.
"""


def model_first() -> bool:
    return (os.getenv("MAX_MODEL_FIRST", "1") or "1").strip().lower() not in ("0", "false", "no", "off")


def shortcut_allowed(name: str) -> bool:
    """True when the named pre-model intercept may answer."""
    if not model_first():
        return True
    return name in KEPT_SHORTCUTS


# ── exact quote-number lookup (the one quote shortcut that stays) ─────────────
_EST = re.compile(r"\bEST-\d{4}-\d{2,4}\b", re.I)
_SPANISH = re.compile(r"[¿¡áéíóúñ]|\b(?:la|el|del|cotizaci[oó]n|m[aá]ndame|env[ií]ame|aqu[ií]|cu[aá]l|qu[eé]|est[aá]|dame)\b", re.I)
_EMAIL_ASK = re.compile(r"\b(?:e-?mail|mail|inbox|gmail)\b", re.I)
_OTHER_ASK = re.compile(
    r"\b(?:and|also|then|compare|vs|versus|change|update|edit|revise|reprice|add|remove|delete|approve|"
    r"create|make|new|draft|why|how|explain|breakdown|line items?|deposit)\b", re.I)


def is_exact_quote_lookup(message: Optional[str]) -> bool:
    """'Status of EST-2026-297?', 'EST-2026-298 total?', 'send me EST-2026-295 here'. One number, nothing else asked."""
    t = (message or "").strip()
    if not t or len(t) > 90 or len(t.split()) > 10 or t.count("?") > 1:
        return False
    if len({n.upper() for n in _EST.findall(t)}) != 1:
        return False
    return not (_SPANISH.search(t) or _EMAIL_ASK.search(t) or _OTHER_ASK.search(t))


# ── web pre-search ────────────────────────────────────────────────────────────
_RESEARCH = re.compile(
    r"\b(?:research|look\s+(?:it\s+)?up\s+online|search\s+(?:the\s+)?(?:web|online|internet)|google\s+it|"
    r"news|noticias|latest\s+on|what'?s\s+(?:new|the\s+latest)\s+in|investiga\w*|busca\s+en\s+internet|sources?|citations?)\b",
    re.I)
_PERSONAL_OR_BUSINESS = re.compile(
    r"\b(?:i|i'm|me|my|mine|we|our|us|you|your|u|max|empire\w*|workroom|nelma\w*|quote\w*|estimate\w*|invoice\w*|"
    r"est-\d|client\w*|customer\w*|job\w*|deposit\w*|drawing\w*|docs?|documents?|pdfs?|files?|e-?mail\w*|inbox|pin|"
    r"dahlia|dalia|nehal|marley\w*|willard|bassett|naomi|phil+ip+|travelers|claim|whatsapp|voice|chat|app|portal|"
    r"loading|attachments?|upload\w*|banquette\w*|basket\s*weave\w*|basketweave\w*|devon|hyattsville|"
    r"mockup\w*|visual\s+reference|diagram\w*|site[- ]?photos?|upholstery|padded\s*bar|v-set|h-set|"
    r"panel\s+(?:count|comparison|basket)|best\s+possible\s+solution)\b", re.I)


def wants_research(message: Optional[str]) -> bool:
    return bool(_RESEARCH.search(message or ""))


def should_pre_search(message: Optional[str], legacy: bool) -> bool:
    """Pre-run web_search before the model only for research/news asks or public facts.

    legacy is the old decision (performative search request or is_factual_question).
    Questions about Rafael, his business, his files or Max himself never get a web
    pre-search; the model can still call web_search itself if it needs to.
    """
    if not model_first():
        return legacy
    if wants_research(message):
        return True
    return bool(legacy) and not _PERSONAL_OR_BUSINESS.search(message or "")


# ── truth guard without canned replies ────────────────────────────────────────
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_ACK_FAILURE = re.compile(r"\b(?:fail\w*|didn'?t|did not|couldn'?t|could not|error|not sent|wasn'?t|isn'?t|unable)\b", re.I)


def _claim_phrases(failures: Iterable[str]) -> list[str]:
    out = []
    for f in failures:
        m = re.search(r"[Cc]laim '([^']+)'|claim ['\"]([^'\"]+)['\"]", f)
        if m:
            out.append((m.group(1) or m.group(2) or "").strip())
        out.extend(n.upper() for n in _EST.findall(f))
        if "PIN" in f:
            out.append("PIN")
        m = re.search(r"file-content claim ['\"]([^'\"]{4,80})", f)
        if m:
            out.append(m.group(1))
    return [p for p in out if p]


def _drop_sentences(text: str, phrases: list[str]) -> str:
    if not phrases:
        return text
    lowered = [p.lower() for p in phrases]
    kept_lines = []
    for line in (text or "").split("\n"):
        parts = re.split(r"(?<=[.!?])\s+", line)
        parts = [p for p in parts if not any(ph in p.lower() for ph in lowered)]
        joined = " ".join(parts).rstrip()
        if joined.strip() or not line.strip():
            kept_lines.append(joined)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept_lines)).strip()


def enforce_truth(message: Optional[str], response_text: str, tool_results: Any) -> tuple[str, list[str]]:
    """Same checks as runtime_truth_enforcer.enforce_runtime_truth_response, but the
    reply Rafael sees keeps everything that is supported. Unsupported claim sentences
    (no tool proof, unknown quote numbers, PIN asks) are dropped; a failed send or
    tool is said plainly. Internal reasons go to the log only."""
    from app.services.max.runtime_truth_enforcer import (
        enforce_runtime_truth_response, runtime_truth_failures, strip_unverified_badge,
    )
    if not model_first():
        return enforce_runtime_truth_response(message, response_text, tool_results)
    failures, warnings = runtime_truth_failures(tool_results, user_message=message, response_text=response_text)
    if not failures:
        cleaned, badge_warnings = strip_unverified_badge(response_text, tool_results)
        return cleaned, list(warnings) + list(badge_warnings)
    logger.warning("truth check adjusted reply: %s", "; ".join(dict.fromkeys(failures))[:500])
    tool_failures = [f for f in failures if re.match(r"^[a-z_]+: ", f) and "claim" not in f.lower()]
    text = _drop_sentences(response_text or "", _claim_phrases(failures))
    if tool_failures and not _ACK_FAILURE.search(text or ""):
        tool, _, why = tool_failures[0].partition(": ")
        why = re.sub(r"\s+", " ", why).strip()[:140]
        note = f"That step didn't go through ({tool.replace('_', ' ')}: {why}), so nothing was done."
        text = f"{text}\n\n{note}".strip() if text else note
    if len(re.findall(r"\w+", text or "")) < 6:
        text = UNCONFIRMED_TEXT
    return text, list(warnings)


# ── final reply cleanup ───────────────────────────────────────────────────────
_GUARD_LINE = re.compile(
    r"^.*(?:has no structured proof object|MAX must (?:say|include)|Present-tense action claim|"
    r"theater-detector|BLOCK_PARSE_POLICY|_tool_block_parse_error).*$\n?", re.I | re.M)
_STATUS_BLOCK = re.compile(
    r"\n*\*\*Status\*\*\s*\n+\s*\*\*Done\*\*.*?(?:\*\*To finish\*\*[^\n]*(?:\n(?!\n)[^\n]*)*|\Z)", re.S)
_STEPS_BLOCK = re.compile(r"\n*\*\*Steps completed\*\*\s*\n(?:\s*[-•].*(?:\n|$))+", re.M)
_QUALITY_DISCLAIMER = re.compile(
    r"\n*⚠️\s*(?:One or more actions encountered errors\. Results may be incomplete\.|_?Low confidence — please verify\._?|_?Quality check flagged potential issues with this response\._?)\s*"
)
_LABEL_HEADER = re.compile(
    r"^\s*(?:#{1,6}\s*)?\**\s*(?:verified(?: facts)?|max'?s inference|inference|sources?|status|done|not done|"
    r"to finish|heads-?up|summary|details|what i (?:scanned|found|did not (?:scan|find)|can(?:not|'t)? see|can see))\b[^\n]{0,60}?\**\s*:?\s*$",
    re.I)
_HEADER = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")
_SOURCES_HEAD = re.compile(r"^\s*(?:#{1,6}\s*)?\**sources?\**\s*:?\s*$", re.I)
_URL = re.compile(r"https?://[^\s)\]>]+")


def _first_source_line(lines: list[str]) -> str:
    for line in lines:
        m = _URL.search(line)
        if m:
            domain = re.sub(r"^https?://(?:www\.)?", "", m.group(0)).split("/")[0]
            return f"Source: {domain}"
    return ""


def _drop_sources_block(text: str) -> str:
    lines = text.split("\n")
    out, i = [], 0
    while i < len(lines):
        if _SOURCES_HEAD.match(lines[i]):
            j = i + 1
            block = []
            while j < len(lines) and (not lines[j].strip() or re.match(r"^\s*(?:\d+[.)]|[-*•])\s", lines[j])):
                block.append(lines[j])
                j += 1
            src = _first_source_line(block)
            if src and not _URL.search("\n".join(out)):
                out.append(src)
            i = j
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def _plain_headers(text: str) -> str:
    out = []
    for line in text.split("\n"):
        if _SOURCES_HEAD.match(line):
            out.append(line)  # handled by _drop_sources_block
            continue
        if _LABEL_HEADER.match(line):
            continue
        m = _HEADER.match(line)
        if m:
            title = m.group(1).strip().strip("*").strip()
            out.append(f"{title}:" if title and not title.endswith((":", "?", ".")) else title)
            continue
        out.append(line)
    return "\n".join(out)


def clean_reply(text: Optional[str], message: Optional[str] = None) -> str:
    """Last pass before Rafael sees a reply: no internal text; plain format unless research was asked."""
    if not text or not model_first():
        return text or ""
    t = str(text)
    if t.strip() == "IMAGE_NOT_AVAILABLE":
        return ATTACHMENT_MISSING_TEXT
    t = _GUARD_LINE.sub("", t)
    t = _STATUS_BLOCK.sub("", t)
    t = _STEPS_BLOCK.sub("\n", t)
    t = _QUALITY_DISCLAIMER.sub("\n", t)
    if not wants_research(message):
        t = _plain_headers(t)
        t = _drop_sources_block(t)
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    return t or UNCONFIRMED_TEXT


# ── pre-lookups (2026-10-07): named client / quote / job, job visuals, weather, daily brief ──
# The model sometimes answered from memory (brief) instead of looking up, and dropped the key
# facts. When a message names one of Rafael's clients, a quote number or a job, the lookup runs
# BEFORE the model and its result goes into context, so the answer is grounded in real data.
_CLIENTS = (
    # (pattern, search_quotes query, find_files query)
    (re.compile(r"\b(?:dahlia|dalia|nehal|elrefai)\b", re.I), "Dahlia", "Dahlia"),
    (re.compile(r"\bmarley'?s?\b|\bhyattsville\b|\bdevon\b|\bbasket\s*weave\b|\bbasketweave\b|\bseat\s*backs?\b", re.I),
     "Marley", "marleys"),
    (re.compile(r"\b(?:phil+ip+e?|naomi|bassett)\b|\bwall\s+unit\b", re.I), "Naomi", "philipp naomi"),
    (re.compile(r"\bwillard\b", re.I), "Willard", "Willard"),
)
_VISUAL = re.compile(
    r"\b(?:mock[- ]?ups?|mick[- ]?ups?|mockup|mock|drawings?|drwings?|drawigs?|diagrams?|renders?|renderings?|"
    r"visuals?|bisual|pictures?|pics?|images?|layouts?|previews?|sketch\w*|basket\s*weave|basketweave)\b", re.I)
_VISUAL_ASK = re.compile(r"\b(?:show|see|send|share|give|get|pull|mockup|mock|mick|drawing|drwing|visual|bisual|reference)\w*", re.I)
_DOC = re.compile(
    r"\b(?:docs?|documents?|pdfs?|files?|addendum|invoices?|led|lighting|spec\w*|photos?|contract|final)\b|\bwall\s+unit\b", re.I)
_QUOTEY = re.compile(r"\b(?:quotes?|estimates?|cotizaci[oó]n\w*|total|phase|status|latest|last|deposit|price|draft)\b", re.I)
_WEATHER = re.compile(r"\b(?:weather|forecast|rain\w*|temperature|clima|lluvia)\b", re.I)
_WEATHER_CITY = re.compile(r"\b(?:in|en|for)\s+([A-Z][A-Za-z.]+(?:[ ,]+[A-Z][A-Za-z.]+)?)")
_BRIEF = re.compile(
    r"\b(?:brief\s+me|briefing|rundown|run\s+down|on\s+my\s+plate|today'?s\s+(?:jobs|work|plan|agenda)|"
    r"(?:what'?s|what\s+is)\s+(?:on\s+)?(?:for\s+)?today|my\s+day|agenda|resumen\s+de\s+hoy)\b", re.I)
_DOC_WORDS = re.compile(r"\b(?:addendum|led|lighting|mockups?|basketweave|wall\s+unit|invoice|final|drawing|layout|comparison)\b", re.I)


def _clients_in(text: str) -> list[tuple[str, str]]:
    return [(sq, ff) for pat, sq, ff in _CLIENTS if pat.search(text or "")]


def _recent_context(history: Any, n: int = 4) -> str:
    out = []
    for h in list(history or [])[-n:]:
        c = h.get("content") if isinstance(h, dict) else getattr(h, "content", "")
        out.append(str(c or ""))
    return "\n".join(out)


def is_job_visual_request(message: Optional[str], history: Any = None) -> bool:
    t = message or ""
    if not _VISUAL.search(t):
        return False
    return bool(_VISUAL_ASK.search(t)) and bool(_clients_in(t) or _clients_in(_recent_context(history)) or
                                                re.search(r"\b(?:job|client|seat\s*back|banquette)\b", t, re.I))


def prelookup_calls(message: Optional[str], history: Any = None, channel: Optional[str] = None) -> list[dict]:
    """Tool calls to run before the model sees the message (model-first mode only)."""
    if not model_first():
        return []
    t = (message or "").strip()
    if not t or wants_research(t):
        return []
    calls: list[dict] = []
    nums = []
    for n in _EST.findall(t):
        if n.upper() not in nums:
            nums.append(n.upper())
    for n in nums[:3]:
        calls.append({"tool": "get_quote", "quote_id": n})
    clients = _clients_in(t)
    if is_job_visual_request(t, history):
        ctx_clients = clients or _clients_in(_recent_context(history))
        ff = ctx_clients[0][1] if ctx_clients else ""
        kind = "mockup" if re.search(r"mock|mick|basket", t, re.I) or re.search(r"basket", _recent_context(history), re.I) else "drawing"
        calls.append({"tool": "find_files", "query": f"{ff} {kind}".strip(), "limit": 10})
        return calls
    if _WEATHER.search(t):
        m = _WEATHER_CITY.search(t)
        calls.append({"tool": "get_weather", "city": (m.group(1).strip(" ,.") if m else "Hyattsville")})
        return calls
    if _BRIEF.search(t):
        calls += [{"tool": "get_tasks", "limit": 10}, {"tool": "list_quotes_awaiting_review"},
                  {"tool": "pipeline_followups"}]
        return calls
    for sq, ff in clients[:2]:
        if _DOC.search(t):
            words = " ".join(dict.fromkeys(w.lower() for w in _DOC_WORDS.findall(t)))
            calls.append({"tool": "find_files", "query": f"{ff} {words}".strip(), "limit": 10})
            if _QUOTEY.search(t):
                calls.append({"tool": "search_quotes", "query": sq})
        else:
            calls.append({"tool": "search_quotes", "query": sq})
    return calls


def active_jobs_section(max_chars: int = 3500) -> str:
    """'Active jobs' section of the Chief e brief (for brief-me asks)."""
    try:
        from app.services.max.chief_e_brief import load_chief_e_brief
        text = load_chief_e_brief() or ""
    except Exception:
        return ""
    m = re.search(r"^##\s*Active jobs[^\n]*\n(.*?)(?=^##\s|\Z)", text, re.S | re.M)
    return (m.group(1).strip()[:max_chars]) if m else ""


def prelookup_message(message: Optional[str], results: list[tuple[str, str]], history: Any = None) -> str:
    """System note with the pre-lookup results. results: [(tool, rendered result)]."""
    if not results:
        return ""
    parts = ["Looked up before you answer (real results from his data; use them, do not say you still need to look):"]
    for tool, body in results:
        parts.append(f"[{tool}] {body}")
    rules = ["Answer short, but keep the key facts from these results: client name, quote numbers, totals, status, file names."]
    if is_job_visual_request(message, history):
        rules.append("This is a job visual request: name the actual file(s) found above (file name and folder) and share the "
                     "best one with share_file (path = the file path) if he asked to see or send it. Never describe the "
                     "design in words instead of the file, never use search_images or the web.")
    if _BRIEF.search(message or ""):
        jobs = active_jobs_section()
        if jobs:
            parts.append("[Chief e brief: active jobs]\n" + jobs)
        rules.append("List each active job by name with its next step (one '- ' line each), then what waits on his tap.")
    parts.append(" ".join(rules))
    return "\n\n".join(parts)


# ── 2026-10-08: no unrequested sends ────────────────────────────────────────────────────────────
# Rafael: "find / show / look up" must never auto-email. Email (or a WhatsApp push from Studio) only
# when he asked to send / email / forward, or said yes to Max's offer to send.
_SEND_ASK = re.compile(
    r"\b(?:send|sent|resend|e-?mail|mail\s+(?:it|me|them|this|that)|forward|fwd|attach|text\s+me|whats\s?app\s+me|"
    r"m[aá]nd[ae]|m[aá]ndame|m[aá]ndalo|m[aá]ndamel[oa]s?|env[ií]a|env[ií]ame|env[ií]alo|reenv[ií]a|correo)\b", re.I)
_VOICE_ONLY = re.compile(r"\bvoice\s*(?:message|note|memo|msg)\b|\baudio\b|\bnota\s+de\s+voz\b", re.I)
_EMAIL_WORD = re.compile(r"\b(?:e-?mail|correo|pdf|attach|inbox|gmail)\b", re.I)
_AFFIRM = re.compile(r"^\s*(?:yes|yeah|yep|yup|ok(?:ay)?|sure|go|go ahead|do it|please|send it|si|s[ií]|dale|claro|hazlo|"
                     r"yes please|please do|ok send|ok go)[\s.!,]*$", re.I)
_OFFERED_SEND = re.compile(r"\b(?:send|e-?mail|forward|attach|share)\b", re.I)
EMAIL_SEND_TOOLS = {"send_email", "send_quote_email"}


def _last_assistant(history: Any) -> str:
    for h in reversed(list(history or [])):
        role = h.get("role") if isinstance(h, dict) else getattr(h, "role", "")
        if role == "assistant":
            c = h.get("content") if isinstance(h, dict) else getattr(h, "content", "")
            return str(c or "")
    return ""


def asked_to_send(message: Optional[str], history: Any = None) -> bool:
    """True when the latest message asks to send/email/forward (or says yes to an offer to send)."""
    t = message or ""
    if _SEND_ASK.search(t):
        # "send me like a voice message ... status" is a voice-style answer, not an email.
        if _VOICE_ONLY.search(t) and not _EMAIL_WORD.search(t):
            return False
        return True
    if _AFFIRM.match(t) and _OFFERED_SEND.search(_last_assistant(history)[-600:]):
        return True
    return False


def unrequested_send_error(tool_call: dict, message: Optional[str], history: Any = None,
                           channel: Optional[str] = None) -> Optional[str]:
    """Return an error for an outbound send Rafael did not ask for, else None. Never rewrites the call."""
    name = str((tool_call or {}).get("tool") or "").strip()
    if name in EMAIL_SEND_TOOLS:
        kind = "email"
    elif name == "share_file":
        via = str(tool_call.get("via") or tool_call.get("channel") or "studio").strip().lower()
        if via in ("mail", "gmail", "email"):
            kind = "email"
        elif via in ("wa", "whats app", "whatsapp") and (channel or "").lower() != "whatsapp":
            kind = "WhatsApp message"
        else:
            return None  # Studio link, or a file into the WhatsApp chat he is writing from
    else:
        return None
    if asked_to_send(message, history):
        return None
    return (f"Not sent: Rafael asked to find/show/look this up, not to send it, so no {kind} went out. "
            "Answer here with what you found (in Studio use share_file with via=\"studio\" for a link) "
            "and offer to email it if he wants.")


# ── 2026-10-08: no unrequested companion quotes ─────────────────────────────────────────────────
# EST-2026-300 (U-only copy of EST-2026-299) was created next to the quote Rafael asked for.
QUOTE_CREATE_TOOLS = {"create_engine_quote", "create_quick_quote", "create_quote", "photo_to_quote", "create_v2_quote"}
_MULTI_QUOTE_ASK = re.compile(
    r"\b(?:two|2|three|3|four|4|both|each|separate(?:ly)?|split|another|second|other|option|options|alternat\w*|"
    r"phases?|per\s+(?:bench|room|piece|area|section)|quotes|estimates|cotizaciones|dos|tres|cada|separad[ao]s?|otra)\b",
    re.I)


def unrequested_companion_quote_error(tool_call: dict, message: Optional[str], history: Any,
                                      tool_results: Any) -> Optional[str]:
    """Second quote creation in one turn without Rafael asking for more than one -> error to the model."""
    name = str((tool_call or {}).get("tool") or "").strip()
    if name not in QUOTE_CREATE_TOOLS:
        return None
    prior = []
    for e in tool_results or []:
        if isinstance(e, dict) and e.get("tool") in QUOTE_CREATE_TOOLS and e.get("success"):
            r = e.get("result") or {}
            prior.append(str(r.get("quote_number") or r.get("quote_id") or "a quote") if isinstance(r, dict) else "a quote")
    if not prior:
        return None
    t = message or ""
    if _MULTI_QUOTE_ASK.search(t):
        return None
    if _AFFIRM.match(t) and _MULTI_QUOTE_ASK.search(_last_assistant(history)[-800:]):
        return None
    return (f"Not created: Rafael asked for one quote and {prior[0]} was already created this turn. "
            "A companion, split or alternate quote needs his explicit ask; mention it in one line if useful.")
