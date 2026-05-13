"""
MAX Artifact Parser — parse, validate, and sanitize artifact JSON blocks from model output.

MAX produces artifacts as fenced JSON blocks in its text response:
    MAX_VISIBLE_RESPONSE: [summary]
    MAX_ARTIFACT_JSON:
    ```json
    {...}
    ```

This module extracts, validates, and sanitizes those blocks server-side.
"""

import json
import re
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ArtifactPayload(BaseModel):
    """Validated artifact payload — enforced safety defaults applied on parse."""
    id: str
    artifact_type: str  # Literal["plain_text", "markdown_report", "html_artifact", "react_component_proposal"]
    title: str
    description: Optional[str] = None
    content_format: str  # Literal["text", "markdown", "html", "json", "tsx"]
    content: str
    source: str = "max"
    mode: str = "review_only"
    requires_approval: bool = False
    allowed_actions: List[str] = Field(default_factory=list)
    safety: Dict[str, bool] = Field(
        default_factory=lambda: {
            "scripts_allowed": False,
            "external_network_allowed": False,
            "sandboxed": True,
            "sanitized": True,
        }
    )
    metadata: Optional[Dict[str, Any]] = None

    def apply_safety_defaults(self) -> None:
        """Enforce safety rules based on artifact type. Mutates self."""
        if self.artifact_type == "html_artifact":
            self.safety = {
                "scripts_allowed": False,
                "external_network_allowed": False,
                "sandboxed": True,
                "sanitized": True,
            }
            self.requires_approval = True
            self.allowed_actions = [
                "approve", "reject", "request_changes",
                "export_html", "copy_source", "open_fullscreen"
            ]
        elif self.artifact_type == "react_component_proposal":
            self.requires_approval = True
            self.allowed_actions = [
                "approve", "reject", "request_changes",
                "copy_source", "open_fullscreen"
            ]
        elif self.artifact_type == "markdown_report":
            self.allowed_actions = ["copy_source", "open_fullscreen"]
        else:  # plain_text
            self.allowed_actions = ["copy_source"]


# Regex: match artifact JSON fence block.
# Two patterns supported:
#   1. MAX_ARTIFACT_JSON:\n```json ... ```
#   2. ```json\n{ "id": ..., "artifact_type": ... } ```
#      (model sometimes omits the MAX_ARTIFACT_JSON label and jumps straight to the fence)
ARTIFACT_BLOCK_RE = re.compile(
    r"(?:MAX_ARTIFACT_JSON\s*:\s*)?```json\s*(.*?)```",
    re.DOTALL | re.IGNORECASE
)


def strip_dangerous_html(html: str) -> str:
    """Strip dangerous HTML: scripts, event handlers, javascript: URLs, iframes, forms, external resources."""
    cleaned = html

    # Remove <script> tags
    before = cleaned
    cleaned = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", "", cleaned, flags=re.IGNORECASE)
    had_script = cleaned != before

    # Remove inline event handlers (onclick, onload, onerror, etc.)
    before = cleaned
    cleaned = re.sub(r'\bon\w+\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>]+)', "", cleaned, flags=re.IGNORECASE)
    had_handlers = cleaned != before

    # Remove javascript: URLs
    before = cleaned
    cleaned = re.sub(r"javascript\s*:", "", cleaned, flags=re.IGNORECASE)
    had_js = cleaned != before

    # Remove external src/href (but keep internal # anchors)
    before = cleaned
    cleaned = re.sub(
        r'\s(src|href)\s*=\s*["\'](?:https?|ftp)://[^"\']+["\']',
        "",
        cleaned,
        flags=re.IGNORECASE
    )
    had_external = cleaned != before

    # Remove iframes, objects, embeds, forms
    before = cleaned
    cleaned = re.sub(r"<(?:iframe|object|embed|form)\b[^>]*>[\s\S]*?</(?:iframe|object|embed|form)>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<(?:iframe|object|embed|form)\b[^>]*/?>", "", cleaned, flags=re.IGNORECASE)
    had_iframe = cleaned != before

    return cleaned


def parse_max_artifact_blocks(text: str) -> List[ArtifactPayload]:
    """
    Extract and validate all MAX_ARTIFACT_JSON fence blocks from text.

    Safety defaults are applied per-artifact-type server-side.
    Invalid blocks are skipped silently — plain text fallback always works.
    """
    blocks: List[ArtifactPayload] = []

    for match in ARTIFACT_BLOCK_RE.finditer(text):
        try:
            data = json.loads(match.group(1))
            artifact = ArtifactPayload(**data)
            artifact.apply_safety_defaults()

            # Backend sanitization for html_artifact
            if artifact.artifact_type == "html_artifact":
                artifact.content = strip_dangerous_html(artifact.content)

            blocks.append(artifact)
        except (json.JSONDecodeError, Exception):
            continue  # Skip invalid — fall back to plain text

    return blocks


def extract_visible_response(text: str) -> str:
    """
    Remove MAX_ARTIFACT_JSON fence blocks from visible response text.
    Returns clean visible text with artifact JSON removed.
    """
    cleaned = ARTIFACT_BLOCK_RE.sub("", text)
    return cleaned.strip()