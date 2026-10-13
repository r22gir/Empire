"""LuxeForge designer mood boards — images, registry swatches, notes.

Shareable read-only via token. Isolated JSON storage under EMPIRE_DATA_DIR.
Does not touch the Sprint I fabric selection board.
"""
from __future__ import annotations

import json
import os
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.services.data_paths import data_root
from app.services.fabric_code_catalog import lookup_code
from app.services.measurements import inches_to_fraction, pair_inches

SHARE_FORBIDDEN_KEYS = (
    "brand", "supplier", "supplier_sku", "supplier_url", "vendor",
)
SHARE_SWATCH_KEYS = (
    "id", "fabric_code", "color", "material_type", "specs", "backing",
    "width_inches", "hex", "size_fraction", "width_fraction", "height_fraction",
    "uncoded",
)


def mood_boards_dir() -> Path:
    override = os.getenv("EMPIRE_LUXE_MOOD_DIR")
    root = Path(override) if override else data_root() / "luxeforge" / "mood_boards"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _path(board_id: str) -> Path:
    return mood_boards_dir() / f"{board_id}.json"


def _index_path() -> Path:
    return mood_boards_dir() / "_index.json"


def _load_index() -> dict[str, str]:
    path = _index_path()
    if not path.exists():
        return {}
    with open(path) as fh:
        return json.load(fh)


def _save_index(index: dict[str, str]) -> None:
    with open(_index_path(), "w") as fh:
        json.dump(index, fh, indent=2)


def resolve_swatch_code(code: Optional[str]) -> Optional[dict[str, Any]]:
    """Registry row or None when the swatch is left uncoded. Never invents codes."""
    return lookup_code(code)


def _decorate_swatch(swatch: dict[str, Any]) -> dict[str, Any]:
    out = dict(swatch)
    for key in SHARE_FORBIDDEN_KEYS:
        out.pop(key, None)
    registry = resolve_swatch_code(out.get("fabric_code"))
    if registry is None:
        out["fabric_code"] = None
        out["uncoded"] = True
        out.pop("color", None)
        out.pop("material_type", None)
        out.pop("specs", None)
    else:
        out["fabric_code"] = registry["code"]
        out["uncoded"] = False
        out["color"] = registry.get("color")
        out["material_type"] = registry.get("material_type")
        out["specs"] = registry.get("specs")
        out["backing"] = registry.get("backing")
        out["width_inches"] = registry.get("width_inches")
    if out.get("width_in") is not None or out.get("height_in") is not None:
        out["size_fraction"] = pair_inches(out.get("width_in"), out.get("height_in"))
    return out


def _decorate_image(image: dict[str, Any]) -> dict[str, Any]:
    out = dict(image)
    if out.get("width_in") is not None or out.get("height_in") is not None:
        out["size_fraction"] = pair_inches(out.get("width_in"), out.get("height_in"))
        if out.get("width_in") is not None:
            out["width_fraction"] = inches_to_fraction(out.get("width_in"))
        if out.get("height_in") is not None:
            out["height_fraction"] = inches_to_fraction(out.get("height_in"))
    return out


def _decorate(board: dict[str, Any]) -> dict[str, Any]:
    out = dict(board)
    out["images"] = [_decorate_image(img) for img in out.get("images") or []]
    out["swatches"] = [_decorate_swatch(s) for s in out.get("swatches") or []]
    out["notes"] = list(out.get("notes") or [])
    return out


def _save(board: dict[str, Any]) -> dict[str, Any]:
    decorated = _decorate(board)
    with open(_path(decorated["id"]), "w") as fh:
        json.dump(decorated, fh, indent=2)
    index = _load_index()
    index[decorated["share_token"]] = decorated["id"]
    _save_index(index)
    return decorated


def list_boards() -> list[dict[str, Any]]:
    boards = []
    for path in sorted(mood_boards_dir().glob("*.json")):
        if path.name.startswith("_"):
            continue
        with open(path) as fh:
            raw = json.load(fh)
        boards.append({
            "id": raw["id"],
            "title": raw.get("title"),
            "designer": raw.get("designer"),
            "client_name": raw.get("client_name"),
            "share_token": raw.get("share_token"),
            "image_count": len(raw.get("images") or []),
            "swatch_count": len(raw.get("swatches") or []),
            "updated_at": raw.get("updated_at"),
        })
    return boards


def get_board(board_id: str) -> Optional[dict[str, Any]]:
    path = _path(board_id)
    if not path.exists():
        return None
    with open(path) as fh:
        return _decorate(json.load(fh))


def get_board_by_token(token: str) -> Optional[dict[str, Any]]:
    index = _load_index()
    board_id = index.get(token)
    if not board_id:
        # Fallback scan if index is stale
        for path in mood_boards_dir().glob("*.json"):
            if path.name.startswith("_"):
                continue
            with open(path) as fh:
                raw = json.load(fh)
            if raw.get("share_token") == token:
                return _decorate(raw)
        return None
    return get_board(board_id)


def create_board(
    title: str,
    designer: str = "",
    client_name: str = "",
    description: str = "",
) -> dict[str, Any]:
    now = _now()
    board = {
        "id": uuid.uuid4().hex[:12],
        "title": title.strip() or "Untitled mood board",
        "designer": designer.strip(),
        "client_name": client_name.strip(),
        "description": description.strip(),
        "images": [],
        "swatches": [],
        "notes": [],
        "share_token": secrets.token_urlsafe(18),
        "created_at": now,
        "updated_at": now,
        "module": "mood_board",
    }
    return _save(board)


def update_board(board_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    board = get_board(board_id)
    if not board:
        raise KeyError(f"Mood board '{board_id}' not found")
    allowed = {"title", "designer", "client_name", "description"}
    for key, value in patch.items():
        if key in allowed and value is not None:
            board[key] = value
    board["updated_at"] = _now()
    return _save(board)


def delete_board(board_id: str) -> bool:
    board = get_board(board_id)
    if not board:
        return False
    index = _load_index()
    index.pop(board.get("share_token"), None)
    _save_index(index)
    path = _path(board_id)
    if path.exists():
        path.unlink()
    return True


def add_image(board_id: str, url: str, caption: str = "", width_in: Any = None, height_in: Any = None) -> dict[str, Any]:
    board = get_board(board_id)
    if not board:
        raise KeyError(f"Mood board '{board_id}' not found")
    if not (url or "").strip():
        raise ValueError("Image URL is required")
    image = {
        "id": uuid.uuid4().hex[:10],
        "url": url.strip(),
        "caption": caption.strip(),
        "width_in": width_in,
        "height_in": height_in,
        "added_at": _now(),
    }
    board["images"].append(_decorate_image(image))
    board["updated_at"] = _now()
    return _save(board)


def add_swatch(
    board_id: str,
    fabric_code: Optional[str] = None,
    name: str = "",
    hex_color: str = "",
    notes: str = "",
    width_in: Any = None,
    height_in: Any = None,
) -> dict[str, Any]:
    board = get_board(board_id)
    if not board:
        raise KeyError(f"Mood board '{board_id}' not found")
    registry = resolve_swatch_code(fabric_code)
    swatch = {
        "id": uuid.uuid4().hex[:10],
        "fabric_code": registry["code"] if registry else None,
        "name": name.strip(),
        "hex": (hex_color or "").strip() or "#c9a84c",
        "notes": notes.strip(),
        "width_in": width_in,
        "height_in": height_in,
        "added_at": _now(),
    }
    board["swatches"].append(_decorate_swatch(swatch))
    board["updated_at"] = _now()
    return _save(board)


def add_note(board_id: str, text: str) -> dict[str, Any]:
    board = get_board(board_id)
    if not board:
        raise KeyError(f"Mood board '{board_id}' not found")
    if not (text or "").strip():
        raise ValueError("Note text is required")
    board["notes"].append({
        "id": uuid.uuid4().hex[:10],
        "text": text.strip(),
        "created_at": _now(),
    })
    board["updated_at"] = _now()
    return _save(board)


def remove_item(board_id: str, collection: str, item_id: str) -> dict[str, Any]:
    board = get_board(board_id)
    if not board:
        raise KeyError(f"Mood board '{board_id}' not found")
    if collection not in {"images", "swatches", "notes"}:
        raise ValueError("collection must be images, swatches, or notes")
    board[collection] = [item for item in board.get(collection) or [] if item.get("id") != item_id]
    board["updated_at"] = _now()
    return _save(board)


def rotate_share_token(board_id: str) -> dict[str, Any]:
    board = get_board(board_id)
    if not board:
        raise KeyError(f"Mood board '{board_id}' not found")
    old = board.get("share_token")
    board["share_token"] = secrets.token_urlsafe(18)
    board["updated_at"] = _now()
    index = _load_index()
    if old:
        index.pop(old, None)
    _save_index(index)
    return _save(board)


def _public_swatch(swatch: dict[str, Any]) -> dict[str, Any]:
    decorated = _decorate_swatch(swatch)
    public = {k: decorated.get(k) for k in SHARE_SWATCH_KEYS if k in decorated}
    public["uncoded"] = bool(decorated.get("uncoded") or not decorated.get("fabric_code"))
    return public


def share_projection(board: dict[str, Any]) -> dict[str, Any]:
    """Read-only share payload: no brand, supplier, or write handles."""
    images = [
        {
            "id": img.get("id"),
            "url": img.get("url"),
            "caption": img.get("caption"),
            "size_fraction": img.get("size_fraction"),
            "width_fraction": img.get("width_fraction"),
            "height_fraction": img.get("height_fraction"),
        }
        for img in board.get("images") or []
    ]
    notes = [{"id": n.get("id"), "text": n.get("text")} for n in board.get("notes") or []]
    return {
        "id": board.get("id"),
        "title": board.get("title"),
        "designer": board.get("designer"),
        "client_name": board.get("client_name"),
        "description": board.get("description"),
        "images": images,
        "swatches": [_public_swatch(s) for s in board.get("swatches") or []],
        "notes": notes,
        "read_only": True,
        "module": "mood_board",
    }
