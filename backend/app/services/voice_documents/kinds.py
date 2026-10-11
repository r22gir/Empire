"""Pluggable document kinds. Handlers read edition config; they do not price."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class DraftDocument:
    kind: str
    status: str
    persisted: bool
    sent: bool = False
    summary: str = ""
    payload: dict = field(default_factory=dict)
    stub: bool = False


Handler = Callable[..., DraftDocument]

_HANDLERS: dict[str, Handler] = {}


def register_handler(kind: str, handler: Handler) -> None:
    _HANDLERS[kind] = handler


def get_handler(kind: str) -> Optional[Handler]:
    return _HANDLERS.get(kind)


def registered_kinds() -> tuple[str, ...]:
    return tuple(sorted(_HANDLERS))


def ensure_handlers_loaded() -> None:
    from app.services.voice_documents import handlers as _handlers  # noqa: F401

    _ = _handlers
