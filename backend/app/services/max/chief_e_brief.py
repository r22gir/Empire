"""Chief e brief loader (2026-10-04).

Chief e is Rafael's cross-business assistant. A nightly routine writes a
condensed Markdown brief of what Chief e knows (hard rules, pricing, doc
rules, active jobs, claims, preferences, recent changes) to

    $EMPIRE_DATA_DIR/brain/chief_e_brief.md   (default ~/empire-data/...)

This module loads that brief into Max's context for Rafael's MAIN edition
only. It is a strict no-op when:
  * the file is missing, empty or unreadable;
  * the process is a family edition (EMPIRE_EDITION set to anything other
    than "main", e.g. "amp" / Max-e on :8011 or "maxine" on :8012), or any
    relevant path (data dir, brief path, checkout) points into a family
    edition (/data/amp, /data/maxine, empire-amp, empire-maxine).

The brief is capped (default ~12k tokens, ~4 chars/token). When it must be
trimmed, the hard-rules, pricing and doc-rule sections are kept first and
the remaining sections fill the leftover budget in their original order.
The rendered result is cached by (path, mtime_ns, size), so the file is
re-read only when the nightly routine rewrites it.
"""
from __future__ import annotations

import logging
import os
import re
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger("max.chief_e_brief")

BRIEF_FILENAME = "chief_e_brief.md"
DEFAULT_MAX_TOKENS = 12_000
CHARS_PER_TOKEN = 4
FAMILY_MARKERS = ("/data/amp", "/data/maxine", "empire-amp", "empire-maxine")
FAMILY_EDITIONS_OK = ("", "main")

# Section titles (H2) that must survive trimming, in priority order.
PRIORITY_PATTERNS = (
    re.compile(r"hard\s*rules?|non[- ]?negotiable", re.I),
    re.compile(r"pric|rate", re.I),
    re.compile(r"doc|format", re.I),
)

# Defensive scrub: the brief is written without secrets, but never let a
# credential-looking token reach a model prompt if one slips in.
_SECRET_RES = (
    re.compile(r"\b(sk|pk|rk)-[A-Za-z0-9_\-]{16,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}"),
    re.compile(r"\b\d{8,10}:[A-Za-z0-9_\-]{30,}\b"),  # telegram bot token
    re.compile(r"(?i)\b(password|passwd|api[_ -]?key|secret|token|pin)\s*[:=]\s*\S+"),
)

POINTER = (
    "This is Chief e's brief: Chief e is Rafael's cross-business assistant "
    "(Grok Bot) and keeps the long-term picture across all of his businesses. "
    "Treat the facts below as current founder context; when a fact here "
    "conflicts with an older memory, the brief wins (newest wins). For big "
    "cross-business decisions (strategy, money across businesses, family "
    "editions, growth bets, legal or claims calls) you may suggest Rafael "
    "bring it to Chief e as well."
)

_cache_lock = threading.Lock()
_cache: dict = {"key": None, "value": ""}


# ── edition / path guards ────────────────────────────────────────────────
def data_dir() -> Path:
    return Path(os.getenv("EMPIRE_DATA_DIR") or (Path.home() / "empire-data"))


def brief_path() -> Path:
    return data_dir() / "brain" / BRIEF_FILENAME


def _has_family_marker(p: object) -> bool:
    try:
        s = str(Path(str(p)).expanduser().resolve())
    except Exception:
        s = str(p)
    return any(m in s for m in FAMILY_MARKERS)


def is_main_edition(path: Optional[Path] = None) -> bool:
    """True only for Rafael's main edition (never AMP/Max-e or Maxine)."""
    edition = (os.getenv("EMPIRE_EDITION") or "").strip().lower()
    if edition not in FAMILY_EDITIONS_OK:
        return False
    candidates = [data_dir(), Path(__file__)]
    if path is not None:
        candidates.append(path)
    return not any(_has_family_marker(c) for c in candidates)


# ── trimming ─────────────────────────────────────────────────────────────
def _scrub(text: str) -> str:
    for rx in _SECRET_RES:
        text = rx.sub("[redacted]", text)
    return text


def _split_sections(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Split on H2 headings. Returns (preamble, [(title, block), ...])."""
    parts = re.split(r"(?m)^(?=##\s)", text)
    preamble = ""
    sections: list[tuple[str, str]] = []
    for part in parts:
        if part.startswith("## "):
            title = part.splitlines()[0][3:].strip()
            sections.append((title, part))
        else:
            preamble += part
    return preamble, sections


def _priority(title: str) -> int:
    for i, rx in enumerate(PRIORITY_PATTERNS):
        if rx.search(title):
            return i
    return len(PRIORITY_PATTERNS)


def _clip_block(block: str, budget: int) -> str:
    if len(block) <= budget:
        return block
    cut = block[: max(0, budget - 30)]
    nl = cut.rfind("\n")
    if nl > 0:
        cut = cut[:nl]
    return cut.rstrip() + "\n- …[section trimmed]\n"


def trim_brief(text: str, max_chars: int) -> str:
    """Fit `text` into `max_chars`, rules/pricing/doc sections first."""
    text = text.strip() + "\n"
    if len(text) <= max_chars:
        return text
    preamble, sections = _split_sections(text)
    preamble = _clip_block(preamble, min(len(preamble), max_chars // 10))
    budget = max_chars - len(preamble) - 120
    indexed = list(enumerate(sections))
    ordered = sorted(indexed, key=lambda it: (_priority(it[1][0]), it[0]))
    kept: dict[int, str] = {}
    for idx, (_title, block) in ordered:
        if budget <= 80:
            break
        piece = _clip_block(block, budget)
        kept[idx] = piece
        budget -= len(piece)
    body = "".join(kept[i] for i in sorted(kept))
    dropped = len(sections) - len(kept)
    note = f"\n_[brief trimmed to fit; {dropped} section(s) omitted]_\n" if dropped else "\n_[brief trimmed to fit]_\n"
    return (preamble + body).rstrip() + "\n" + note


def max_chars() -> int:
    try:
        tokens = int(os.getenv("CHIEF_E_BRIEF_MAX_TOKENS") or DEFAULT_MAX_TOKENS)
    except ValueError:
        tokens = DEFAULT_MAX_TOKENS
    return max(1000, tokens) * CHARS_PER_TOKEN


# ── public API ───────────────────────────────────────────────────────────
def load_chief_e_brief(path: Optional[Path] = None) -> str:
    """Return the (trimmed, scrubbed) brief text, or "" when not applicable."""
    p = Path(path) if path is not None else brief_path()
    if not is_main_edition(p):
        return ""
    try:
        st = p.stat()
    except (FileNotFoundError, NotADirectoryError, PermissionError):
        return ""
    except OSError as e:
        logger.debug("chief_e brief stat failed: %s", e)
        return ""
    limit = max_chars()
    key = (str(p), st.st_mtime_ns, st.st_size, limit)
    with _cache_lock:
        if _cache["key"] == key:
            return _cache["value"]
    try:
        raw = p.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        logger.debug("chief_e brief read failed: %s", e)
        return ""
    value = trim_brief(_scrub(raw), limit) if raw.strip() else ""
    with _cache_lock:
        _cache["key"] = key
        _cache["value"] = value
    return value


def render_chief_e_section(path: Optional[Path] = None) -> str:
    """Prompt section for get_system_prompt_with_brain ("" = no-op)."""
    brief = load_chief_e_brief(path)
    if not brief.strip():
        return ""
    return f"## Chief e Brief (founder context, refreshed nightly)\n{POINTER}\n\n{brief.strip()}"


def clear_cache() -> None:
    with _cache_lock:
        _cache["key"] = None
        _cache["value"] = ""
