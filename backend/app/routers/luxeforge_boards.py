"""LuxeForge designer selection boards.

Preview-only conversion. Never writes live quotes, invoices, or clients.
Not on the public Luxe hostname allowlist.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.services.luxeforge.catalog import catalog_bundle
from app.services.luxeforge.selection_board import (
    board_to_estimate,
    demo_board,
    ensure_board_schema,
    list_boards,
    load_board,
    save_board,
)

router = APIRouter(tags=["luxeforge-boards"])


class SelectionIn(BaseModel):
    id: str
    qty: Optional[float] = None
    treatment: Optional[str] = None
    notes: Optional[str] = None


class BoardIn(BaseModel):
    title: Optional[str] = None
    client_name: Optional[str] = None
    project_name: Optional[str] = None
    treatment: Optional[str] = "drapery"
    notes: Optional[str] = None
    selections: List[SelectionIn] = Field(default_factory=list)


@router.get("/catalog")
def board_catalog():
    return catalog_bundle()


@router.get("/boards")
def get_boards():
    with get_db() as conn:
        ensure_board_schema(conn)
        boards = list_boards(conn)
    return {
        "boards": boards,
        "demo": demo_board(),
        "wrote_live": False,
    }


@router.get("/boards/demo")
def get_demo_board():
    board = demo_board()
    return {"board": board, "estimate": board_to_estimate(board), "wrote_live": False, "wrote_quote": False}


@router.get("/boards/{board_id}")
def get_board(board_id: str):
    if board_id == "demo":
        board = demo_board()
        return {"board": board, "estimate": board_to_estimate(board), "wrote_live": False}
    with get_db() as conn:
        ensure_board_schema(conn)
        board = load_board(conn, board_id)
    if not board:
        raise HTTPException(404, "Board not found")
    return {"board": board, "estimate": board_to_estimate(board), "wrote_live": False}


@router.post("/boards")
def create_board(req: BoardIn):
    with get_db() as conn:
        ensure_board_schema(conn)
        board = save_board(conn, req.model_dump())
    return {"board": board, "wrote_live": False, "wrote_quote": False}


@router.put("/boards/{board_id}")
def update_board(board_id: str, req: BoardIn):
    if board_id == "demo":
        board = {**demo_board(), **{k: v for k, v in req.model_dump().items() if v is not None}}
        board["id"] = "demo"
        return {"board": board, "estimate": board_to_estimate(board), "persisted": False, "wrote_live": False}
    with get_db() as conn:
        ensure_board_schema(conn)
        try:
            board = save_board(conn, req.model_dump(), board_id=board_id)
        except KeyError:
            raise HTTPException(404, "Board not found")
    return {"board": board, "estimate": board_to_estimate(board), "wrote_live": False}


@router.post("/boards/{board_id}/estimate")
def preview_estimate(board_id: str, req: Optional[BoardIn] = None):
    """Compose a proposal/estimate preview. Never writes a live quote."""
    if board_id == "demo":
        board = demo_board()
        if req:
            board.update({k: v for k, v in req.model_dump().items() if v is not None})
            board["id"] = "demo"
    else:
        with get_db() as conn:
            ensure_board_schema(conn)
            board = load_board(conn, board_id)
        if not board:
            raise HTTPException(404, "Board not found")
        if req:
            incoming = req.model_dump()
            if incoming.get("selections") is not None:
                board["selections"] = incoming["selections"]
            for key in ("title", "client_name", "project_name", "treatment", "notes"):
                if incoming.get(key) is not None:
                    board[key] = incoming[key]
    estimate = board_to_estimate(board)
    return {
        "board": board,
        "estimate": estimate,
        "wrote_quote": False,
        "wrote_live": False,
        "sent": False,
    }


@router.post("/estimate/preview")
def estimate_from_payload(req: BoardIn):
    """Stateless preview from a payload. Writes nothing."""
    board = req.model_dump()
    board.setdefault("id", "preview")
    return {
        "board": board,
        "estimate": board_to_estimate(board),
        "wrote_quote": False,
        "wrote_live": False,
        "sent": False,
    }
