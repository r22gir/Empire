"""CNC cut-list nesting API. Fraction-only measurements. PDF per-sheet yield."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.services.cnc.inches import InchFormatError
from app.services.cnc.nesting import NestError, nest_cut_list
from app.services.cnc.pdf import render_nest_pdf

router = APIRouter()


class SizeIn(BaseModel):
    width: str
    length: str


class PartIn(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    width: Optional[str] = None
    length: Optional[str] = None
    wood: Optional[SizeIn] = None
    foam: Optional[SizeIn] = None
    fabric: Optional[SizeIn] = None
    grain: str = "with"
    qty: int = 1
    notes: Optional[str] = None

    def to_payload(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "grain": self.grain,
            "qty": self.qty,
            "notes": self.notes or "",
        }
        if self.wood:
            data["wood"] = self.wood.model_dump()
        elif self.width and self.length:
            data["wood"] = {"width": self.width, "length": self.length}
        if self.foam:
            data["foam"] = self.foam.model_dump()
        if self.fabric:
            data["fabric"] = self.fabric.model_dump()
        return data


class NestRequest(BaseModel):
    title: str = "CNC cut list"
    job_id: Optional[str] = None
    notes: str = ""
    kerf: str = "1/8"
    machine_width: str = "29 1/2"
    tile_length: str = "29 1/2"
    sheet_width: str = "29 1/2"
    sheet_length: str = "96"
    foam_sheet_width: str = "24"
    foam_sheet_length: str = "72"
    fabric_usable_width: str = "53"
    parts: list[PartIn] = Field(default_factory=list)


def _run_nest(body: NestRequest) -> dict[str, Any]:
    payload = body.model_dump()
    payload["parts"] = [p.to_payload() for p in body.parts]
    try:
        return nest_cut_list(payload)
    except (NestError, InchFormatError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/cnc/nest")
async def api_nest(body: NestRequest):
    return _run_nest(body)


@router.post("/cnc/nest/pdf")
async def api_nest_pdf(body: NestRequest):
    result = _run_nest(body)
    pdf = render_nest_pdf(result)
    filename = "cnc-cut-list.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
