"""Central MiniMax / LLM hidden-reasoning stripper.

MiniMax-M2/M3 (and other reasoning models) emit chain-of-thought in several
shapes: ``<think>`` blocks, ``reasoning_content`` fields, provider-specific
tokens, and streamed partial tags. That text is English self-talk. It must
never be shown, saved, or used to build tool / web_search queries.

Every consumer — reply, chat history, search-query builder, tool parser,
streaming — calls this module. Do not re-implement think-stripping elsewhere.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

# XML-ish / MiniMax / DeepSeek / Qwen-style wrappers.
# MiniMax-M3 leaked as orphan ``</mm:think>`` (no open tag) on 2026-10-21.
# Accept optional provider prefixes: mm:think, minimax:thinking, foo:think.
_TAG_ALT = r"(?:[A-Za-z][\w.-]*:)?(?:think(?:ing)?|thought|reason(?:ing)?)"

_COMPLETE_TAG_RE = re.compile(
    rf"<(?:{_TAG_ALT})\b[^>]*>.*?</(?:{_TAG_ALT})>",
    re.IGNORECASE | re.DOTALL,
)
# Innermost first: do not let an inner </think> close an outer <mm:think>.
_INNERMOST_COMPLETE_RE = re.compile(
    rf"<(?:{_TAG_ALT})\b[^>]*>(?:(?!<(?:{_TAG_ALT})\b).)*?</(?:{_TAG_ALT})>",
    re.IGNORECASE | re.DOTALL,
)
_UNCLOSED_TAG_RE = re.compile(
    rf"<(?:{_TAG_ALT})\b[^>]*>.*\Z",
    re.IGNORECASE | re.DOTALL,
)
_ORPHAN_CLOSE_RE = re.compile(rf"</(?:{_TAG_ALT})>", re.IGNORECASE)
_ORPHAN_OPEN_RE = re.compile(rf"<(?:{_TAG_ALT})\b[^>]*>", re.IGNORECASE)

_SPECIAL_COMPLETE_RE = re.compile(
    r"(?:◁think▷.*?◁/think▷)|(?:<\|\s*think(?:ing)?\s*\|>.*?<\|\s*/?\s*think(?:ing)?\s*\|>)",
    re.IGNORECASE | re.DOTALL,
)
_SPECIAL_UNCLOSED_RE = re.compile(
    r"(?:◁think▷.*\Z)|(?:<\|\s*think(?:ing)?\s*\|>.*\Z)",
    re.IGNORECASE | re.DOTALL,
)
_SPECIAL_ORPHAN_RE = re.compile(
    r"(?:◁/?think▷)|(?:<\|\s*/?\s*think(?:ing)?\s*\|>)",
    re.IGNORECASE,
)

_FENCE_COMPLETE_RE = re.compile(
    r"```(?:thinking|reason|reasoning|thought)\b[^\n]*\n.*?```",
    re.IGNORECASE | re.DOTALL,
)
_FENCE_UNCLOSED_RE = re.compile(
    r"```(?:thinking|reason|reasoning|thought)\b[^\n]*.*\Z",
    re.IGNORECASE | re.DOTALL,
)

_ANSWER_WRAP_RE = re.compile(
    r"<(?:answer|final|回答)>([\s\S]*?)</(?:answer|final|回答)>",
    re.IGNORECASE,
)

# Provider payload keys that hold hidden reasoning, never user-visible text.
REASONING_FIELD_NAMES = (
    "reasoning_content",
    "reasoning",
    "thinking",
    "thought",
    "reasoning_details",
    "reasoning_text",
)
REASONING_PART_TYPES = frozenset({
    "reasoning",
    "thinking",
    "thought",
    "reason",
    "reasoning_content",
})

# Open-tag prefixes the stream filter must hold until it can decide.
_STREAM_OPEN_TAGS = (
    "<think>",
    "<thinking>",
    "<thought>",
    "<reason>",
    "<reasoning>",
    "<minimax:thinking>",
    "<minimax:think>",
    "<mm:thinking>",
    "<mm:think>",
    "◁think▷",
    "<|think|>",
    "<|thinking|>",
    "```thinking",
    "```reason",
    "```reasoning",
    "```thought",
)
_STREAM_CLOSE_TAGS = (
    "</think>",
    "</thinking>",
    "</thought>",
    "</reason>",
    "</reasoning>",
    "</minimax:thinking>",
    "</minimax:think>",
    "</mm:thinking>",
    "</mm:think>",
    "◁/think▷",
    "<|/think|>",
    "<|/thinking|>",
    "</|think|>",
    "</|thinking|>",
)

# Oct 21 leak quoted internal developer rules with no opening tag.
_INTERNAL_RULE_LEAK = re.compile(
    r"(?is)(?:developer says|not ask tokens/?secrets|tokens/?secrets|"
    r"tools absent from(?: current)? prompt|internal (?:developer )?rules?)"
)
_ENGLISH_PLANNER_START = re.compile(
    r"(?is)\A(?:The user\b|I should\b|I need to\b|Let(?:'|’)s\b|"
    r"Let me think\b|The assistant\b|developer says\b|Tools absent\b|"
    r"secret plan\b|Note to (?:self|developer)\b)"
)

_TOOL_QUERY_KEYS = (
    "query",
    "q",
    "search",
    "text",
    "message",
    "content",
    "prompt",
    "question",
)


def _drop_before_orphan_close(text: str) -> str:
    """Orphan close tag = reasoning with no open. Drop everything before it.

    Night Lab 2026-10-22: ``secret plan</mm:think>Hola`` kept the plan
    because the old stripper only deleted the tag.
    """
    last = None
    for match in _ORPHAN_CLOSE_RE.finditer(text):
        last = match
    if last is None:
        return text
    return text[last.end():]


def _strip_untagged_reasoning_preamble(text: str) -> str:
    """Drop English internal-rule / planner preambles with no think tags."""
    if not text:
        return text
    paragraphs = re.split(r"\n\s*\n", text)
    if len(paragraphs) == 1:
        snippet = paragraphs[0].strip()
        # Whole-reply English that quotes developer rules is a leak, not an answer.
        if _INTERNAL_RULE_LEAK.search(snippet) and _ENGLISH_PLANNER_START.match(snippet):
            return ""
        return text
    kept: list[str] = []
    dropping = True
    for part in paragraphs:
        snippet = part.strip()
        if not snippet:
            continue
        leak = bool(_INTERNAL_RULE_LEAK.search(snippet))
        planner = bool(_ENGLISH_PLANNER_START.match(snippet))
        if dropping and (leak or planner):
            continue
        dropping = False
        kept.append(part)
    return "\n\n".join(kept) if kept else text


def _strip_complete_blocks(text: str) -> str:
    """Peel complete think blocks from the inside out.

    One ``.*?`` pass stops at the first close tag, so nested
    ``<mm:think>…<think>…</think> leftover</mm:think>`` used to leave an
    orphan close that ate the visible prefix. Repeat until stable.
    """
    cleaned = text
    for _ in range(8):
        nxt = _INNERMOST_COMPLETE_RE.sub("", cleaned)
        nxt = _SPECIAL_COMPLETE_RE.sub("", nxt)
        nxt = _FENCE_COMPLETE_RE.sub("", nxt)
        if nxt == cleaned:
            nxt = _COMPLETE_TAG_RE.sub("", nxt)
        if nxt == cleaned:
            return cleaned
        cleaned = nxt
    return cleaned


def strip_thinking(text: str | None, *, trim_edges: bool = True) -> str:
    """Remove hidden reasoning from a complete (or flushed) model string."""
    if not text:
        return "" if text is None else text

    cleaned = _strip_complete_blocks(str(text))
    # Unclosed think at end-of-string: drop it, do not keep the inner text.
    cleaned = _UNCLOSED_TAG_RE.sub("", cleaned)
    cleaned = _SPECIAL_UNCLOSED_RE.sub("", cleaned)
    cleaned = _FENCE_UNCLOSED_RE.sub("", cleaned)
    # Orphan close: the Oct 21 shape. Drop the reasoning, not just the tag.
    cleaned = _drop_before_orphan_close(cleaned)
    cleaned = _ORPHAN_CLOSE_RE.sub("", cleaned)
    cleaned = _ORPHAN_OPEN_RE.sub("", cleaned)
    cleaned = _SPECIAL_ORPHAN_RE.sub("", cleaned)
    cleaned = _ANSWER_WRAP_RE.sub(r"\1", cleaned)
    cleaned = _strip_untagged_reasoning_preamble(cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    if trim_edges:
        cleaned = cleaned.strip()
    return cleaned


def raw_visible_text_from_provider_payload(payload: Any) -> str:
    """Extract content fields only — never ``reasoning_content`` / thinking parts.

    Does not strip ``<think>`` tags. Streaming callers must run a
    ``ThinkingStreamFilter`` on this raw text so split tags stay hidden.
    """
    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, list):
        return _join_visible_parts(payload)
    if not isinstance(payload, dict):
        return ""

    content = payload.get("content")
    if isinstance(content, list):
        return _join_visible_parts(content)
    if isinstance(content, str):
        return content
    if content:
        return str(content)
    return ""


def visible_text_from_provider_payload(payload: Any) -> str:
    """User-visible text from a complete chat message, delta, or part list.

    Never concatenates ``reasoning_content`` (or siblings) into the reply.
    That was the 'appears twice' history bug: thinking field + think-tagged
    content both landed in the saved assistant turn.
    """
    return strip_thinking(raw_visible_text_from_provider_payload(payload))


def _join_visible_parts(parts: Iterable[Any]) -> str:
    chunks: list[str] = []
    for part in parts:
        if isinstance(part, str):
            chunks.append(part)
            continue
        if not isinstance(part, dict):
            continue
        ptype = str(part.get("type") or "").strip().lower()
        if ptype in REASONING_PART_TYPES:
            continue
        if any(part.get(key) and key in REASONING_FIELD_NAMES for key in part):
            # A reasoning-only part may still carry a 'text' field — skip it.
            if ptype.startswith("reason") or ptype.startswith("think"):
                continue
        text = part.get("text")
        if text is None:
            text = part.get("content")
        if isinstance(text, str) and text:
            chunks.append(text)
    return "".join(chunks)


def sanitize_history_messages(messages: list | None) -> list:
    """Return a shallow copy of history with thinking stripped from content."""
    if not messages:
        return []
    cleaned: list = []
    for item in messages:
        if not isinstance(item, dict):
            cleaned.append(item)
            continue
        copy = dict(item)
        content = copy.get("content")
        if isinstance(content, str):
            copy["content"] = strip_thinking(content)
        elif isinstance(content, list):
            copy["content"] = strip_thinking(_join_visible_parts(content))
        for key in REASONING_FIELD_NAMES:
            copy.pop(key, None)
        cleaned.append(copy)
    return cleaned


def sanitize_tool_query(query: str | None) -> str:
    """Strip thinking from a tool / web_search query string."""
    return strip_thinking(query)


def sanitize_tool_call(tool_call: dict | None) -> dict:
    """Strip thinking from model-supplied string fields on a tool call."""
    if not isinstance(tool_call, dict):
        return {}
    cleaned = dict(tool_call)
    for key in _TOOL_QUERY_KEYS:
        value = cleaned.get(key)
        if isinstance(value, str):
            cleaned[key] = strip_thinking(value)
    return cleaned


_THINK_NAME_RE = re.compile(
    rf"^{_TAG_ALT}$",
    re.IGNORECASE,
)
_THINK_CANDIDATES = ("think", "thinking", "thought", "reason", "reasoning")


def _xml_tag_name(tag: str) -> str | None:
    if not (tag.startswith("<") and tag.endswith(">") and len(tag) >= 3):
        return None
    inner = tag[1:-1].strip()
    if not inner:
        return None
    return inner.split(None, 1)[0]


def _is_think_xml_tag(tag: str) -> bool:
    name = _xml_tag_name(tag)
    if not name:
        return False
    if name.startswith("/"):
        name = name[1:]
    return bool(_THINK_NAME_RE.match(name))


def _name_could_be_think(name: str, *, closed: bool) -> bool:
    if not name:
        return not closed
    if _THINK_NAME_RE.match(name):
        return True
    if closed:
        return False
    lower = name.lower()
    if ":" in lower:
        _prefix, _, rest = lower.partition(":")
        if not _prefix:
            return False
        return rest == "" or any(cand.startswith(rest) for cand in _THINK_CANDIDATES)
    if any(cand.startswith(lower) for cand in _THINK_CANDIDATES):
        return True
    return bool(re.match(r"^[A-Za-z][\w.-]*$", name))


def _xml_buffer_could_be_think(buf: str) -> bool:
    if not buf.startswith("<"):
        return False
    inner = buf[1:]
    if not inner:
        return True
    if inner[0] == "/":
        inner = inner[1:]
        if not inner:
            return True
    if inner[0] in " \t\n!?":
        return False
    name = ""
    for ch in inner:
        if ch in " \t\n>/":
            return _name_could_be_think(name, closed=True)
        name += ch
    return _name_could_be_think(name, closed=False)


class ThinkingStreamFilter:
    """Stateful filter for streamed tokens with split ``<think>`` tags.

    Per-chunk regex cannot hide reasoning that starts in one chunk and
    ends in the next. Hold tag prefixes; drop everything between a
    recognized open tag and its close tag. Namespaced variants
    (``<mm:think>``, ``<foo:thinking>``) are matched, not just a
    hard-coded list — chunks often split mid-tag.
    """

    def __init__(self) -> None:
        self._mode = "visible"  # visible | thinking | fence
        self._buffer = ""
        self._depth = 0
        self._max_open = max(len(tag) for tag in _STREAM_OPEN_TAGS)
        self._max_close = max(len(tag) for tag in _STREAM_CLOSE_TAGS)

    def feed(self, chunk: str | None) -> str:
        if not chunk:
            return ""
        visible: list[str] = []
        for char in chunk:
            piece = self._consume(char)
            if piece:
                visible.append(piece)
        return "".join(visible)

    def flush(self) -> str:
        """End of stream. Drop leftover thinking; emit a non-tag remainder."""
        if self._mode != "visible":
            self._buffer = ""
            self._depth = 0
            self._mode = "visible"
            return ""
        leftover = self._buffer
        self._buffer = ""
        if leftover and (
            _could_be_open_prefix(leftover) or _xml_buffer_could_be_think(leftover)
        ):
            # Incomplete ``<thi`` / ``<mm:th`` at EOS is not user text.
            if leftover.startswith("<") or leftover.startswith("◁") or leftover.startswith("```"):
                return ""
        return leftover

    def _consume(self, char: str) -> str:
        if self._mode == "visible":
            return self._consume_visible(char)
        return self._consume_hidden(char)

    def _consume_visible(self, char: str) -> str:
        if not self._buffer:
            if _could_be_open_prefix(char) or char == "<":
                self._buffer = char
                return ""
            return char
        self._buffer += char
        if self._buffer.startswith("```") or self._buffer.startswith("◁") or self._buffer.startswith("<|"):
            return self._consume_special_visible()
        if self._buffer.startswith("<"):
            return self._consume_xml_visible()
        flushed = self._buffer
        self._buffer = ""
        return flushed

    def _consume_special_visible(self) -> str:
        lowered = self._buffer.lower()
        exact = [tag for tag in _STREAM_OPEN_TAGS if lowered == tag.lower()]
        longer = [
            tag for tag in _STREAM_OPEN_TAGS
            if tag.lower().startswith(lowered) and len(tag) > len(self._buffer)
        ]
        if exact and not longer:
            self._mode = "fence" if exact[0].startswith("```") else "thinking"
            self._depth = 0 if exact[0].startswith("```") else 1
            self._buffer = ""
            return ""
        if longer and len(self._buffer) <= self._max_open:
            return ""
        flushed = self._buffer
        self._buffer = ""
        return flushed

    def _consume_xml_visible(self) -> str:
        if ">" in self._buffer:
            idx = self._buffer.find(">")
            tag = self._buffer[: idx + 1]
            rest = self._buffer[idx + 1 :]
            self._buffer = ""
            if _is_think_xml_tag(tag):
                name = _xml_tag_name(tag) or ""
                if name.startswith("/"):
                    # Orphan close in visible text. Keep the tag so the
                    # final strip_thinking can drop the reasoning prefix
                    # (``secret plan</mm:think>Hola``).
                    return tag + rest
                self._mode = "thinking"
                self._depth = 1
                return rest
            return tag + rest
        if not _xml_buffer_could_be_think(self._buffer) or len(self._buffer) > 200:
            flushed = self._buffer
            self._buffer = ""
            return flushed
        return ""

    def _consume_hidden(self, char: str) -> str:
        self._buffer += char
        lowered = self._buffer.lower()
        if self._mode == "fence":
            if self._buffer.endswith("```") and len(self._buffer) >= 3:
                self._mode = "visible"
                self._depth = 0
                self._buffer = ""
                return ""
            if len(self._buffer) > 8000:
                self._mode = "visible"
                self._depth = 0
                self._buffer = ""
            return ""
        if char == ">":
            idx = self._buffer.rfind("<")
            if idx >= 0 and _is_think_xml_tag(self._buffer[idx:]):
                name = _xml_tag_name(self._buffer[idx:]) or ""
                if name.startswith("/"):
                    self._depth = max(0, self._depth - 1)
                    self._buffer = ""
                    if self._depth == 0:
                        self._mode = "visible"
                    return ""
                self._depth += 1
                self._buffer = ""
                return ""
        for tag in _STREAM_CLOSE_TAGS:
            if lowered.endswith(tag.lower()):
                self._depth = max(0, self._depth - 1)
                self._buffer = ""
                if self._depth == 0:
                    self._mode = "visible"
                return ""
        for tag in _STREAM_OPEN_TAGS:
            if tag.startswith("```"):
                continue
            if lowered.endswith(tag.lower()):
                self._depth += 1
                self._buffer = ""
                return ""
        if len(self._buffer) > max(self._max_close, 80):
            self._buffer = self._buffer[-max(self._max_close, 80):]
        return ""


def _could_be_open_prefix(text: str) -> bool:
    lowered = text.lower()
    return any(tag.lower().startswith(lowered) for tag in _STREAM_OPEN_TAGS)


def stream_visible_text(chunks: Iterable[str]) -> str:
    """Join streamed chunks after filtering split think tags."""
    filt = ThinkingStreamFilter()
    parts = [filt.feed(chunk) for chunk in chunks]
    parts.append(filt.flush())
    return strip_thinking("".join(parts))
