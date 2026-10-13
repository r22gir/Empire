"""LuxeForge mood-board API. Owner CRUD + token-gated read-only share."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services import luxeforge_mood_board as boards

router = APIRouter(prefix="/luxeforge/mood-boards", tags=["luxeforge-mood-boards"])


class BoardCreate(BaseModel):
    title: str
    designer: str = ""
    client_name: str = ""
    description: str = ""


class BoardUpdate(BaseModel):
    title: Optional[str] = None
    designer: Optional[str] = None
    client_name: Optional[str] = None
    description: Optional[str] = None


class ImageAdd(BaseModel):
    url: str
    caption: str = ""
    width_in: Optional[float] = None
    height_in: Optional[float] = None


class SwatchAdd(BaseModel):
    fabric_code: str = Field(..., description="V###-Color, e.g. V142-Navy")
    name: str = ""
    hex_color: str = ""
    notes: str = ""
    width_in: Optional[float] = None
    height_in: Optional[float] = None


class NoteAdd(BaseModel):
    text: str


@router.get("")
async def list_boards():
    return {"items": boards.list_boards(), "module": "mood_board"}


@router.post("")
async def create_board(req: BoardCreate):
    return boards.create_board(req.title, req.designer, req.client_name, req.description)


@router.get("/share/{token}")
async def shared_board(token: str):
    board = boards.get_board_by_token(token)
    if not board:
        raise HTTPException(404, "Mood board not found")
    # Read-only projection — no write URLs.
    return {
        "id": board["id"],
        "title": board.get("title"),
        "designer": board.get("designer"),
        "client_name": board.get("client_name"),
        "description": board.get("description"),
        "images": board.get("images") or [],
        "swatches": board.get("swatches") or [],
        "notes": board.get("notes") or [],
        "read_only": True,
        "module": "mood_board",
    }


@router.get("/{board_id}")
async def get_board(board_id: str):
    board = boards.get_board(board_id)
    if not board:
        raise HTTPException(404, "Mood board not found")
    return board


@router.put("/{board_id}")
async def update_board(board_id: str, req: BoardUpdate):
    try:
        return boards.update_board(board_id, req.model_dump(exclude_none=True))
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.delete("/{board_id}")
async def delete_board(board_id: str):
    if not boards.delete_board(board_id):
        raise HTTPException(404, "Mood board not found")
    return {"deleted": True}


@router.post("/{board_id}/images")
async def add_image(board_id: str, req: ImageAdd):
    try:
        return boards.add_image(board_id, req.url, req.caption, req.width_in, req.height_in)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/{board_id}/swatches")
async def add_swatch(board_id: str, req: SwatchAdd):
    try:
        return boards.add_swatch(
            board_id, req.fabric_code, req.name, req.hex_color, req.notes, req.width_in, req.height_in,
        )
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/{board_id}/notes")
async def add_note(board_id: str, req: NoteAdd):
    try:
        return boards.add_note(board_id, req.text)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.delete("/{board_id}/{collection}/{item_id}")
async def remove_item(board_id: str, collection: str, item_id: str):
    try:
        return boards.remove_item(board_id, collection, item_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/{board_id}/rotate-share")
async def rotate_share(board_id: str):
    try:
        return boards.rotate_share_token(board_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
