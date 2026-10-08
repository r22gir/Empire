"""Simple rubric for Max regression answers (2026-10-06).

Each answer is scored pass/fail on four categories:
  route     right path/tool (expected tool called, forbidden tools not called,
            asks back when it should, right language)
  grounded  required facts present, known-wrong / invented facts absent,
            no quote numbers that do not exist
  concise   short (word cap), no headers / Sources block unless research was asked
  clean     no internal guard / tool / template text reached Rafael
A question passes overall when all four pass. Pure functions, no I/O.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

CATEGORIES = ("route", "grounded", "concise", "clean")

INTERNAL_PATTERNS = [
    r"IMAGE_NOT_AVAILABLE", r"structured proof", r"\bMAX must\b", r"\*\*Status\*\*", r"\*\*Not done\*\*",
    r"\*\*To finish\*\*", r"Run send_quote_email", r"Email MAX is partial", r"Live Lookup summary",
    r"\[SYSTEM", r"tool block", r"```", r"Verified facts", r"Max's inference", r"theater-detector",
    r"truth[ _]guard", r"runtime check required", r"I need to run a tool before I can confirm", r"couldn't confirm that with a live result",
    r"^Transcript:", r"Brand: Empire Workroom", r"Send was asked and blocked", r"_tool_block_parse_error",
    r"\{\s*\"tool\"\s*:", r"REDACTED_ENV_NAME", r"empire_runtime_truth_check", r"canonical selector",
    r"Here's what's new:\s*\n\s*- Recent live changes", r"MAX read the attached file\. Extracted context",
    r"\bStatus\b\s*\n+\s*\*?\*?Done\*?\*?", r"One or more actions encountered errors",
]
_INTERNAL_RE = [re.compile(p, re.I | re.M) for p in INTERNAL_PATTERNS]
_HEADER_RE = re.compile(r"^\s{0,3}#{1,6}\s+\S", re.M)
_SOURCES_RE = re.compile(r"^\s*(?:#{1,6}\s*)?\**sources?\**\s*:?\s*$", re.I | re.M)
_QUOTE_NUM_RE = re.compile(r"\bEST-\d{4}-\d{2,4}[A-Z]?\b", re.I)
_SPANISH_HINT = re.compile(
    r"\b(?:el|la|los|las|de|del|que|es|est[aá]|para|con|una?|cotizaci[oó]n|noticias|estoy|tu|tienes|"
    r"aqu[ií]|ahora|también|sí|no hay|puedo|quieres)\b", re.I)


_NEGATION = re.compile(r"\b(?:not|no|never|isn'?t|aren'?t|wasn'?t|don'?t|doesn'?t|won'?t|without|instead\s+of|"
                       r"rather\s+than|nor|avoid\w*|zero)\b|n't\b", re.I)


def affirmative_hit(pattern: str, text: str) -> str:
    """Sentence where `pattern` appears WITHOUT a negation before it in the same sentence
    ('it's a yarn weave' fails; 'not a yarn weave' / 'never Unsplash' pass). '' when none (2026-10-07)."""
    for sent in re.split(r"(?<=[.!?])\s+|\n+", text or ""):
        for m in re.finditer(pattern, sent, re.I | re.M):
            if not _NEGATION.search(sent[:m.start()][-60:]):
                return sent.strip()
    return ""


def words(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def _match_any(patterns: Iterable[str], text: str) -> bool:
    return any(re.search(p, text or "", re.I | re.M) for p in patterns)


def internal_hits(text: str) -> list[str]:
    return [p.pattern for p in _INTERNAL_RE if p.search(text or "")]


def is_spanish(text: str) -> bool:
    return len(_SPANISH_HINT.findall(text or "")) >= 3


def _tool_hit(expected: str, called: list[str]) -> bool:
    e = expected.lower()
    return any(c.lower() == e or c.lower().startswith(e) for c in called)


def score_answer(spec: dict[str, Any], record: dict[str, Any], *, known_quotes: set[str] | None = None) -> dict[str, Any]:
    """spec: one fixture question. record: {"text", "tools": [...], "error"?}."""
    exp = spec.get("expect") or {}
    text = str(record.get("text") or "")
    called = [str(t) for t in (record.get("tools") or [])]
    research = bool(exp.get("research"))
    notes: list[str] = []

    # route
    route = True
    if record.get("error") or not text.strip():
        route = False
        notes.append(f"no answer ({record.get('error') or 'empty'})")
    any_tools = exp.get("tools_any") or []
    if any_tools and not any(_tool_hit(t, called) for t in any_tools):
        route = False
        notes.append(f"expected one of {any_tools}, got {called}")
    for t in exp.get("tools_none") or []:
        if _tool_hit(t, called):
            route = False
            notes.append(f"should not call {t}")
    if exp.get("must_ask") and "?" not in text and "¿" not in text:
        route = False
        notes.append("should ask a short question back")
    if exp.get("lang") == "es" and not is_spanish(text):
        route = False
        notes.append("should answer in Spanish")

    # grounded
    grounded = True
    for group in exp.get("must_any") or []:
        group = [group] if isinstance(group, str) else group
        if not _match_any(group, text):
            grounded = False
            notes.append(f"missing fact {group}")
    for pat in exp.get("must_not") or []:
        if re.search(pat, text, re.I | re.M):
            grounded = False
            notes.append(f"wrong/invented: /{pat}/")
    for pat in exp.get("must_not_affirm") or []:
        hit = affirmative_hit(pat, text)
        if hit:
            grounded = False
            notes.append(f"wrong/invented: /{pat}/ ({hit[:60]!r})")
    if known_quotes is not None:
        bad = sorted({q.upper() for q in _QUOTE_NUM_RE.findall(text)} - known_quotes)
        if bad:
            grounded = False
            notes.append(f"unknown quote numbers {bad}")

    # concise
    concise = True
    cap = int(exp.get("max_words") or (300 if research else 120))
    n = words(text)
    if n > cap:
        concise = False
        notes.append(f"{n} words > {cap}")
    if not research and not exp.get("allow_headers"):
        if _HEADER_RE.search(text):
            concise = False
            notes.append("markdown headers")
        if _SOURCES_RE.search(text):
            concise = False
            notes.append("Sources block without a research ask")

    # clean
    hits = internal_hits(text)
    clean = not hits
    if hits:
        notes.append(f"internal text {hits}")

    result = {"route": route, "grounded": grounded, "concise": concise, "clean": clean}
    result["pass"] = all(result[c] for c in CATEGORIES)
    result["words"] = n
    result["notes"] = notes
    return result


def summarize(scores: dict[str, dict[str, Any]]) -> dict[str, Any]:
    total = len(scores)
    out = {c: sum(1 for s in scores.values() if s[c]) for c in CATEGORIES}
    out["pass"] = sum(1 for s in scores.values() if s["pass"])
    out["total"] = total
    return out


def gate(baseline: dict[str, Any], new: dict[str, Any]) -> tuple[bool, list[str]]:
    """Ship only if new >= baseline in every category and better overall."""
    reasons = []
    for c in CATEGORIES:
        if new[c] < baseline[c]:
            reasons.append(f"{c}: {new[c]} < baseline {baseline[c]}")
    if new["pass"] <= baseline["pass"]:
        reasons.append(f"overall: {new['pass']} not better than baseline {baseline['pass']}")
    return (not reasons), reasons
