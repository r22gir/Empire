"""Founder multi-step action loop: no dangling promises, honest status blocks."""
from __future__ import annotations

import re
from typing import Any

from app.services.max.guardrails import (
    founder_action_tools_remaining,
    is_imperative_action_request,
)

FOUNDER_CONTINUATION_MAX_ROUNDS = 3

_DANGLING_PROMISE_RE = re.compile(
    r"(?i)\b("
    r"now\s+generat(?:ing|e)|"
    r"i(?:'ll| will)\s+now|"
    r"next\s+i\s+will|"
    r"sending\s+now|"
    r"emailing\b|"
    r"working\s+on\s+it|"
    r"let\s+me\s+(?:go\s+ahead\s+and\s+)?(?:now\s+)?(?:generate|send|email|create|prepare|build|draft|produce|queue|run|execute)"
    r")\b"
)


def assistant_announces_future_work(text: str | None) -> bool:
    body = (text or "").strip()
    if not body:
        return False
    return bool(_DANGLING_PROMISE_RE.search(body))


# Announced-action guard (2026-10-04): a reply that says it is about to do something
# ("Let me pull up the cost module...", "I'll submit the improvement request",
# "Voy a revisar...") but called no tool in that response is not a final answer.
# The loop continues once or twice with a nudge so Max either calls the tool now
# or answers plainly. Questions back to Rafael (ending in "?") are allowed.
ANNOUNCED_ACTION_MAX_ROUNDS = 2
_ACTION_VERBS = (
    r"check|look(?:\s+(?:into|up|at))?|pull(?:\s+up)?|find|investigate|search|open|grab|get|fetch|review|"
    r"make\s+the\s+change|add|fix|change|build|file|submit|create|draft|prepare|"
    r"set\s+up|dig\s+into|track\s+down|send|email|generate|render|update|run|make|attach|apply|put\s+together|"
    r"start|kick\s+off|do\s+(?:it|that|this)|get\s+(?:it|that|this)\s+done"
)
_ANNOUNCED_ACTION_RE = re.compile(
    r"(?i)(?:"
    r"\blet\s+me\s+(?:go\s+ahead\s+and\s+|quickly\s+|now\s+|first\s+)?(?:" + _ACTION_VERBS + r")\b"
    r"|\bi(?:'ll|\s+will|\s*'m\s+going\s+to|\s+am\s+going\s+to)\s+(?:now\s+|first\s+|quickly\s+|go\s+ahead\s+and\s+)?(?:" + _ACTION_VERBS + r")\b"
    r"|\b(?:one|a)\s+(?:sec|second|moment)\b"
    r"|^\W*(?:on\s+it|got\s+it|will\s+do|doing\s+it\s+now|right\s+away)\b"
    r"|\b(?:creating|sending|generating|building|drafting|updating|adding|rendering|preparing|pulling|emailing|attaching|"
    r"running|starting|fixing|making)\b[^.?!\n]{0,80}\b(?:now|next|shortly|right\s+away|in\s+a\s+(?:sec|moment|minute))\b"
    r"|\b(?:going\s+to|gonna|about\s+to)\s+(?:" + _ACTION_VERBS + r")\b"
    r"|\bvoy\s+a\s+(?:revisar|buscar|consultar|investigar|averiguar|hacer|agregar|añadir|arreglar|crear|preparar|abrir|mirar|ver)\b"
    r"|\bd[ée]jame\s+(?:revisar|buscar|ver|consultar|mirar|averiguar)\b"
    r"|\bun\s+(?:segundo|momento)\b"
    r")"
)


_CONDITIONAL_RE = re.compile(
    r"(?i)\b(?:once|when|if|after|as\s+soon\s+as)\s+you\b|\bsay\s+(?:yes|go|the\s+word)\b|"
    r"\b(?:give|send)\s+me\s+the\s+go-?ahead\b|\bcuando\s+(?:me\s+)?digas\b|\bsi\s+(?:me\s+)?dices\b")


def announces_action_without_tool(text: str | None) -> bool:
    """True when the reply announces an imminent action (and is not just asking Rafael)."""
    body = (text or "").strip()
    if not body or len(body) > 1200:
        return False
    if body.rstrip().endswith("?"):
        return False
    if _CONDITIONAL_RE.search(body):
        return False  # "I'll send it once you say yes" waits on Rafael; it is not an announcement
    return bool(_ANNOUNCED_ACTION_RE.search(body))


_GO_RE = re.compile(
    r"(?i)^\W*(?:go|go\s+ahead|go\s+for\s+it|do\s+it|yes|yep|yeah|ok(?:ay)?|sure|please|proceed|run\s+it|ship\s+it|"
    r"dale|s[ií]|hazlo|adelante|claro)(?:\W+(?:go|do\s+it|please|now|ahead|all|both|everything|that))*\W*$")


def is_go_message(message: str | None) -> bool:
    """'go' / 'yes do it' / 'dale': Rafael approved the plan in Max's previous message."""
    return bool(_GO_RE.match((message or "").strip()))


_OFFER_RE = re.compile(r"(?i)\b(?:want\s+me\s+to|shall\s+i|should\s+i|i\s+can|ready\s+to|say\s+(?:go|the\s+word)|"
                       r"plan|next\s+steps?|i'?d\s+(?:create|send|build|update|draft|add))\b|\?\s*$")


def go_without_action(message: str | None, history: Any, tool_round: int, assistant_text: str | None) -> bool:
    """Rafael said 'go' to an offer/plan and this reply ran no tool: push for the tools, same turn."""
    if tool_round > 0 or not is_go_message(message):
        return False
    body = (assistant_text or "").strip()
    if body.endswith("?") or len(body) > 1200:
        return False
    prev = ""
    for h in reversed(list(history or [])):
        role = h.get("role") if isinstance(h, dict) else getattr(h, "role", "")
        if role == "assistant":
            prev = str((h.get("content") if isinstance(h, dict) else getattr(h, "content", "")) or "")
            break
    return bool(prev and _OFFER_RE.search(prev[-800:]))


def announced_action_nudge(assistant_text: str | None, message: str | None = None) -> str:
    go = ("Rafael just said go to the plan in your previous message: call those tools now, in this reply, "
          "one ```tool``` block per step, then report what actually happened. " if is_go_message(message) else "")
    return go + (
        "Your last reply announced an action but called no tool, so nothing happened. Do not narrate. "
        "Either call the right tool now in a ```tool``` block (for a change to Empire itself, call "
        "request_improvement with his words, then say it will be built on a test copy for his approval), "
        "or, if no tool applies, give the direct answer or ask one short clarifying question. "
        "Never say you don't edit your own code. This nudge never authorizes sending, approving, "
        "paying or deleting anything; those still need Rafael's explicit yes."
    )


def strip_performative_closing(text: str) -> str:
    """Remove trailing sentences that only promise work not yet done."""
    if not text:
        return text
    lines = text.splitlines()
    while lines:
        last = lines[-1].strip()
        if not last:
            lines.pop()
            continue
        if _DANGLING_PROMISE_RE.search(last):
            lines.pop()
            continue
        break
    return "\n".join(lines).strip()


def _quote_ids_from_results(tool_results: list[Any] | None) -> list[str]:
    ids: list[str] = []
    for entry in tool_results or []:
        if not isinstance(entry, dict) or not entry.get("success"):
            continue
        if entry.get("tool") not in ("create_engine_quote", "create_quick_quote", "photo_to_quote"):
            continue
        res = entry.get("result") or {}
        qid = res.get("quote_id") or res.get("id")
        if qid:
            ids.append(str(qid))
    return ids


def _emailed_quote_ids(tool_results: list[Any] | None) -> set[str]:
    emailed: set[str] = set()
    for entry in tool_results or []:
        if not isinstance(entry, dict) or not entry.get("success"):
            continue
        if entry.get("tool") != "send_quote_email":
            continue
        res = entry.get("result") or {}
        qid = res.get("quote_id")
        if qid:
            emailed.add(str(qid))
    return emailed


def founder_action_incomplete_reasons(
    message: str | None,
    tool_results: list[Any] | None,
    assistant_text: str | None = None,
) -> list[str]:
    """Human-readable reasons the founder request is not finished."""
    if not is_imperative_action_request(message):
        return []
    reasons: list[str] = []
    remaining_tools = founder_action_tools_remaining(message, tool_results)
    tool_labels = {
        "create_contact": "Create CRM contact",
        "create_engine_quote": "Create estimate(s) via create_engine_quote",
        "create_quick_quote": "Create quote via create_quick_quote",
        "send_quote_email": "Generate PDF(s) and email via send_quote_email (one call; multiple quote_ids in one email)",
        "send_email": "Send email via send_email",
        "svg_to_pdf": "Generate PDF via send_quote_email (per quote_id)",
    }
    for tool in remaining_tools:
        label = tool_labels.get(tool, tool)
        if label not in reasons:
            reasons.append(label)

    quote_ids = _quote_ids_from_results(tool_results)
    emailed = _emailed_quote_ids(tool_results)
    text = (message or "").lower()
    wants_email = "email" in text or "send " in text
    if wants_email and quote_ids:
        missing = [q for q in quote_ids if q not in emailed]
        if missing and not any("send_quote_email" in r for r in reasons):
            reasons.append(
                f"Email PDFs for quote_id(s) {', '.join(missing)} via send_quote_email"
            )

    for entry in tool_results or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("tool") == "send_quote_email" and not entry.get("success"):
            err = str(entry.get("error") or "blocked")
            reasons.append(f"send_quote_email failed: {err}")

    if assistant_text and assistant_announces_future_work(assistant_text) and not reasons:
        reasons.append("Assistant promised further steps but no matching tools ran")

    return reasons


def should_force_founder_action_continuation(
    message: str | None,
    tool_results: list[Any] | None,
    assistant_text: str | None,
) -> tuple[bool, list[str]]:
    if not is_imperative_action_request(message):
        return False, []
    remaining = founder_action_tools_remaining(message, tool_results)
    promises = assistant_announces_future_work(assistant_text)
    if remaining or promises:
        nudge_tools = list(remaining)
        if promises and not nudge_tools:
            nudge_tools = founder_action_tools_remaining(message, tool_results) or ["send_quote_email"]
        return True, nudge_tools
    return False, []


def founder_continuation_system_nudge(remaining_tools: list[str], assistant_text: str | None) -> str:
    tools = ", ".join(remaining_tools) if remaining_tools else "send_quote_email"
    promise_note = ""
    if assistant_announces_future_work(assistant_text):
        promise_note = (
            " Your last message promised work that has not run yet — do NOT narrate future steps. "
        )
    return (
        "The founder action request is not complete."
        + promise_note
        + f" You MUST call the remaining tools now before any final answer: {tools}. "
        "For estimates, call send_quote_email once with quote_ids (array) or quote_id when emailing "
        "multiple PDFs in one message (PDF generation is included). Use exact line items from the "
        "user message — no recalculation. "
        "Emit valid ```tool``` JSON blocks only; no performative 'now generating' text."
    )


def format_tool_progress_message(entry: dict[str, Any]) -> str:
    tool = str(entry.get("tool") or "?")
    ok = bool(entry.get("success"))
    res = entry.get("result") if isinstance(entry.get("result"), dict) else {}
    err = str(entry.get("error") or "Unknown error")

    if tool == "create_engine_quote" and ok:
        qn = res.get("quote_number") or res.get("quote_id") or "estimate"
        total = res.get("total")
        if isinstance(total, (int, float)):
            return f"✓ Created {qn} (${total:,.2f})"
        return f"✓ Created {qn}"

    if tool == "create_quick_quote" and ok:
        qn = res.get("quote_number") or res.get("quote_id") or "quote"
        return f"✓ Created {qn}"

    if tool == "create_contact" and ok:
        name = res.get("name") or res.get("contact_id") or "contact"
        return f"✓ Contact created ({name})"

    if tool == "send_quote_email":
        if ok:
            to = res.get("to") or res.get("recipient") or "recipient"
            qn = res.get("quote_number") or res.get("quote_id") or ""
            suffix = f" for {qn}" if qn else ""
            return f"✓ PDF generated and emailed to {to}{suffix}"
        low = err.lower()
        if "whitelist" in low or "recipient_not_in" in low or "recipient_authorized" in low:
            return f"✗ Email blocked: {err}"
        if "pdf" in low:
            return f"✗ PDF generation failed: {err}"
        return f"✗ Email failed: {err}"

    if tool == "search_contacts" and ok:
        count = res.get("count")
        if count is not None:
            return f"✓ search_contacts ({count} match(es))"
        return "✓ search_contacts"

    if ok:
        return f"✓ {tool}"
    return f"✗ {tool}: {err}"


_SKIP_STATUS_DONE_TOOLS = frozenset({
    "web_search",
    "web_read",
    "_tool_block_parse_error",
})


def build_step_lines_from_tool_results(tool_results: list[Any] | None) -> list[str]:
    lines: list[str] = []
    for entry in tool_results or []:
        if not isinstance(entry, dict):
            continue
        tool = entry.get("tool")
        if not tool or str(tool).startswith("_"):
            continue
        if str(tool) in _SKIP_STATUS_DONE_TOOLS:
            continue
        lines.append(format_tool_progress_message(entry))
    return lines


def _done_lines(tool_results: list[Any] | None) -> list[str]:
    return [ln for ln in build_step_lines_from_tool_results(tool_results) if ln.startswith("✓")]


def _not_done_lines(
    message: str | None,
    tool_results: list[Any] | None,
    assistant_text: str | None,
) -> list[str]:
    out: list[str] = []
    for entry in tool_results or []:
        if isinstance(entry, dict) and entry.get("tool") == "send_quote_email" and not entry.get("success"):
            out.append(format_tool_progress_message(entry))
    for reason in founder_action_incomplete_reasons(message, tool_results, assistant_text):
        if reason not in out:
            out.append(reason)
    return out


def founder_resume_hint(remaining_tools: list[str], tool_results: list[Any] | None) -> str:
    quote_ids = _quote_ids_from_results(tool_results)
    parts: list[str] = []
    if "send_quote_email" in remaining_tools or any(
        "send_quote_email" in r for r in founder_action_incomplete_reasons("", tool_results, None)
    ):
        if quote_ids:
            parts.append(
                'Say: "Email PDFs for '
                + " and ".join(quote_ids)
                + ' to <recipient> using send_quote_email."'
            )
        else:
            parts.append('Say: "Run send_quote_email for each quote_id to the recipient."')
    if "create_engine_quote" in remaining_tools:
        parts.append('Say: "Create the remaining estimates with create_engine_quote using my line items."')
    if "create_contact" in remaining_tools:
        parts.append('Say: "Create the CRM contact with create_contact."')
    if not parts:
        parts.append("Re-send the founder action request and ask MAX to run the remaining tools.")
    return " ".join(parts)


def _model_first() -> bool:
    try:
        from app.services.max.answer_policy import model_first
        return model_first()
    except Exception:
        return True


def plain_not_done_note(message, tool_results, assistant_text=None) -> str:
    items = []
    for item in _not_done_lines(message, tool_results, assistant_text):
        item = str(item).lstrip("✗ ").strip().rstrip(".")
        if item and item not in items:
            items.append(item)
    if not items:
        return ""
    return "Not done: " + "; ".join(items[:4]) + "."


def format_founder_status_block(
    message: str | None,
    tool_results: list[Any] | None,
    assistant_text: str | None = None,
) -> str:
    done = _done_lines(tool_results)
    not_done = _not_done_lines(message, tool_results, assistant_text)
    remaining_tools = founder_action_tools_remaining(message, tool_results)
    lines = ["**Status**", "", "**Done**"]
    if done:
        lines.extend(f"- {d.lstrip('✓ ').strip()}" if d.startswith("✓") else f"- {d}" for d in done)
    else:
        lines.append("- (none yet)")
    lines.extend(["", "**Not done**"])
    if not_done:
        for item in not_done:
            lines.append(f"- {item.lstrip('✗ ').strip() if item.startswith('✗') else item}")
    else:
        lines.append("- (none)")
    lines.extend(["", "**To finish**", founder_resume_hint(remaining_tools, tool_results)])
    return "\n".join(lines)


def finalize_founder_action_reply(
    message: str | None,
    tool_results: list[Any] | None,
    reply_text: str,
) -> tuple[str, list[str], bool]:
    """Return (reply, step_lines, still_incomplete)."""
    steps = build_step_lines_from_tool_results(tool_results)
    if not is_imperative_action_request(message):
        return reply_text, steps, False

    incomplete_reasons = founder_action_incomplete_reasons(message, tool_results, reply_text)
    still_incomplete = bool(incomplete_reasons) or assistant_announces_future_work(reply_text)

    body = reply_text
    if still_incomplete and _model_first():
        # 2026-10-08 (Rafael): no Status / Done / To finish template, no "say X to finish".
        # One plain sentence says what did not happen and why.
        body = strip_performative_closing(body)
        note = plain_not_done_note(message, tool_results, reply_text)
        if note and note not in body:
            body = (body.rstrip() + "\n\n" + note).strip() if body.strip() else note
    elif still_incomplete:
        body = strip_performative_closing(body)
        status = format_founder_status_block(message, tool_results, reply_text)
        if status not in body:
            body = (body.rstrip() + "\n\n" + status).strip() if body.strip() else status
    elif _model_first():
        pass
    elif len([s for s in steps if s.startswith("✓")]) >= 2:
        summary_lines = ["**Steps completed**"] + [f"- {s}" for s in steps if s.startswith("✓")]
        summary = "\n".join(summary_lines)
        if "**Steps completed**" not in body and "**Status**" not in body:
            body = (body.rstrip() + "\n\n" + summary).strip()

    return body, steps, still_incomplete
