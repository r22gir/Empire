"""Sprint 1d Phase A Fix #3 — theater detector.

Detects chat-model fabrication of tool-call-shaped JSON
({"tool": "...", ...}) when no matching tool was actually executed.
The LLM sometimes outputs this as prose when it cannot find a real tool
to call.

REGEX COVERAGE: {"tool": ...} shape only. Code fences, function-call
text (XML-ish), and multi-line JSON with nested arrays are EXPLICITLY
future work (NOT Phase A).

Hard rule: NEVER fail the response. Returns an Optional[str] that the
runtime_truth_enforcer appends as a WARNING in response metadata
(metadata["runtime_truth_warnings"]) for the founder to see. The warning
is also logged at WARNING level. Responses are NOT blocked.
"""
import re
from typing import Optional


# Match {"tool": "<name>", ...} or {"tool": "<name>"} — non-greedy on values.
# Tolerates: {"tool": "x", "k": "v"}, {"tool": "x"}, with optional spaces.
_TOOL_JSON = re.compile(
    r'\{\s*"tool"\s*:\s*"([^"]+)"(?:\s*,\s*"[^"]+"\s*:\s*'
    r'(?:"[^"]*"|[\d.\-]+|true|false|null|\[[^\]]*\]|\{[^\}]*\}))*\s*\}',
    re.DOTALL,
)


def detect_fabricated_tool_text(
    response_text: str, executed_tool_names: list[str]
) -> Optional[str]:
    """Return a WARNING string if the chat response contains
    {"tool": ...} snippets that did NOT correspond to an actually-executed
    tool call. Returns None when no fabrication is detected.

    The hard rule: NEVER fail the response. This function returns a
    WARNING string only. The caller appends to warnings[] and logs at
    WARNING level; the response is NOT blocked.

    Note: regex covers {"tool": ...} shape only. Future work (NOT
    Phase A): code-fence fabrication, function-call text (XML-ish),
    multi-line JSON with nested arrays.
    """
    if not response_text:
        return None
    executed = {t for t in (executed_tool_names or [])}
    fabricated = []
    for m in _TOOL_JSON.finditer(response_text):
        try:
            tool_name = re.search(r'"tool"\s*:\s*"([^"]+)"', m.group(0)).group(1)
        except (AttributeError, IndexError):
            continue
        if tool_name not in executed:
            fabricated.append(tool_name)
    if not fabricated:
        return None
    # Dedupe, sort, single WARNING string.
    unique = sorted(set(fabricated))
    names = ", ".join(f"'{n}'" for n in unique)
    return (
        f"WARNING (Sprint 1d Phase A theater-detector): chat response "
        f"contains fabricated tool-call JSON for {names} that did NOT "
        f"match any executed tool call. This is the LLM confabulating "
        f"a tool-call shape when it should be honest about not having "
        f"that tool. Regex covers only {{'tool': ...}} shape; code "
        f"fences and function-call text are out of scope (Phase A follow-up)."
    )
