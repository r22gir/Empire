"""ULID-style public ids for BusinessOps rows."""
from __future__ import annotations

import re
import uuid


def new_id(prefix: str) -> str:
    """Return a URL-safe id like `biz_a1b2c3d4e5f60718`."""
    clean = (prefix or "id").strip("_")
    return f"{clean}_{uuid.uuid4().hex[:16]}"


def slugify(value: str, fallback: str = "business") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    slug = slug[:48] or fallback
    return slug


def unique_slug(value: str, suffix: str | None = None) -> str:
    base = slugify(value)
    tail = (suffix or uuid.uuid4().hex[:8]).lower()
    return f"{base}-{tail}"
