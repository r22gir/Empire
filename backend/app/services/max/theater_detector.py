"""Sprint 1d Phase A Fix #3 — theater detector.

Detects chat-model fabrication of tool-call-shaped JSON when no
matching tool was actually executed. The LLM sometimes emits this as
prose when it cannot find a real tool to call (visible to the user as
unrendered JSON in the assistant reply).

REGEX COVERAGE (Phase A + HOTFIX 2026-07-16 b):

  Pre-fix: matched only `{"tool": "<name>", ...}`. The Anthropic
  function-call shape (`{"name": "<tool>", "parameters": {...}}`) and
  the OpenAI tool-call wrapper (`{"name": ..., "arguments": ...}`)
  slipped past — Phase A had this gap because MAX had not yet
  encountered the Anthropic-shape hallucination. The fix: extend
  coverage to `name`-key shapes.

  Hotfix-b: extend to EITHER `tool` OR `name` keys (with optional
  nested `function.name` for OpenAI shapes). The function-name
  extractor tries three patterns in order.

Hard rule: NEVER fail the response. Returns an Optional[str] that the
runtime_truth_enforcer appends as a WARNING in response metadata
(metadata["runtime_truth_warnings"]) for the founder to see. The
warning is also logged at WARNING level. Responses are NOT blocked
unless the caller chooses to hard-block the warning (separate policy
from this detector — kept separate so the detector stays usable from
places that want to surface-but-not-block).

Future work (NOT HOTFIX-b): code-fence fabrication, multi-line JSON
with nested arrays, XML-shaped function-call blocks.
"""
import re
from typing import Optional


# Distinct helper regexes so we can document each shape clearly:
#
# 1. {"tool": "<name>", ...}            (Phase A)
# 2. {"name": "<name>", "parameters":
#       { ... }}                          (Anthropic function-call)
# 3. {"function": {"name": "<name>"},
#       ...}                              (OpenAI tool-call wrapper)
#
# All three are non-greedy on values and tolerate further JSON
# members after the tool-name key. Full JSON parsing is overkill
# here — we want to detect fabrication, not validate JSON.
_TOOL_KEY_RE = re.compile(
    r'\{\s*"tool"\s*:\s*"([^"]+)"(?:\s*,[^}]*)?\}',
    re.DOTALL,
)
_NAME_KEY_RE = re.compile(
    r'\{\s*"name"\s*:\s*"([^"]+)"(?:\s*,[^}]*)?\}',
    re.DOTALL,
)
_FUNCTION_NAME_KEY_RE = re.compile(
    r'\{\s*"function"\s*:\s*\{\s*"name"\s*:\s*"([^"]+)"',
    re.DOTALL,
)

_ALL_SHAPES = (_TOOL_KEY_RE, _NAME_KEY_RE, _FUNCTION_NAME_KEY_RE)


def _iter_fabricated_tool_names(response_text: str):
    """Yield (tool_name, raw_match) for every tool-call-shaped JSON
    snippet in the response text. Each pattern yields the tool name
    regardless of the source key."""
    for pat in _ALL_SHAPES:
        for m in pat.finditer(response_text):
            try:
                yield m.group(1), m.group(0)
            except (AttributeError, IndexError):
                continue


def detect_fabricated_tool_text(
    response_text: str, executed_tool_names: list[str]
) -> Optional[str]:
    """Return a WARNING string if the chat response contains
    tool-call-shaped JSON that did NOT correspond to an actually-
    executed tool call. Returns None when no fabrication is detected.

    Recognized shapes (HOTFIX-b, 2026-07-16):
      - {"tool": "<name>", ...}
      - {"name": "<name>", ...}                   ← Anthropic
      - {"function": {"name": "<name>"}}           ← OpenAI

    Returns a WARNING string (never raises, never blocks).
    """
    if not response_text:
        return None
    executed = {t for t in (executed_tool_names or [])}
    fabricated = []
    seen_snippets: set[str] = set()
    for tool_name, raw in _iter_fabricated_tool_names(response_text):
        # Dedupe by raw snippet so the same shape in the response
        # doesn't double-count.
        if raw in seen_snippets:
            continue
        seen_snippets.add(raw)
        if tool_name not in executed:
            fabricated.append(tool_name)
    if not fabricated:
        return None
    unique = sorted(set(fabricated))
    names = ", ".join(f"'{n}'" for n in unique)
    return (
        f"WARNING (Sprint 1d Phase A theater-detector + HOTFIX 2026-07-16 "
        f"shape extension): chat response contains fabricated tool-call "
        f"JSON for {names} that did NOT match any executed tool call. "
        f"This is the LLM confabulating a tool-call shape when it should "
        f"be honest about not having that tool. Recognized shapes: "
        f"{{'tool': ...}}, {{'name': ...}} (Anthropic function-call), "
        f"{{'function': {{'name': ...}}}} (OpenAI). Code fences and "
        f"XML function-call blocks are out of scope."
    )
