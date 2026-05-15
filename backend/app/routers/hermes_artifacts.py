"""Hermes Knowledge Artifact Layer API (v10)."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.max.hermes_artifact_layer import (
    get_hermes_artifact_layer_status,
    hermes_artifact_export,
    hermes_artifact_get,
    hermes_artifact_search,
    hermes_artifact_supersede,
    hermes_artifact_update_status,
    hermes_artifact_write,
)


router = APIRouter(prefix="/hermes/artifacts", tags=["hermes-artifacts"])


class ArtifactWriteRequest(BaseModel):
    title: str
    artifact_type: str
    content: str
    content_format: str = "html"
    module: Optional[str] = None
    source_agent: str = "max"
    approval_status: str = "draft"
    tags: list[str] = Field(default_factory=list)
    retrieval_keywords: list[str] = Field(default_factory=list)
    supersedes: list[str] = Field(default_factory=list)
    source_prompt: Optional[str] = None
    source_prompt_hash: Optional[str] = None
    source_files: list[str] = Field(default_factory=list)
    source_endpoints: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)


class ArtifactSearchRequest(BaseModel):
    query: Optional[str] = None
    module: Optional[str] = None
    artifact_type: Optional[str] = None
    approval_status: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    current_only: bool = True
    include_superseded: bool = False
    limit: int = 20


class ArtifactUpdateStatusRequest(BaseModel):
    approval_status: str
    notes: Optional[str] = None
    safety_status: Optional[str] = None
    actor_id: Optional[str] = None
    actor_type: Optional[str] = None
    actor_label: Optional[str] = None
    actor_source: Optional[str] = None
    approval_method: Optional[str] = None
    approval_confidence: Optional[str] = None
    actor_note: Optional[str] = None


class ArtifactSupersedeRequest(BaseModel):
    superseded_id: str
    replacement_id: str
    notes: Optional[str] = None
    actor_id: Optional[str] = None
    actor_type: Optional[str] = None
    actor_label: Optional[str] = None
    actor_source: Optional[str] = None
    approval_method: Optional[str] = None
    approval_confidence: Optional[str] = None


@router.get("/status")
def artifact_layer_status():
    return get_hermes_artifact_layer_status()


@router.post("/write")
def artifact_write(req: ArtifactWriteRequest):
    try:
        return hermes_artifact_write(
            title=req.title,
            artifact_type=req.artifact_type,
            content=req.content,
            content_format=req.content_format,
            module=req.module,
            source_agent=req.source_agent,
            approval_status=req.approval_status,
            tags=req.tags,
            retrieval_keywords=req.retrieval_keywords,
            supersedes=req.supersedes,
            source_prompt=req.source_prompt,
            source_prompt_hash=req.source_prompt_hash,
            source_files=req.source_files,
            source_endpoints=req.source_endpoints,
            provenance=req.provenance,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/search")
def artifact_search(req: ArtifactSearchRequest):
    return hermes_artifact_search(
        query=req.query,
        module=req.module,
        artifact_type=req.artifact_type,
        approval_status=req.approval_status,
        tags=req.tags,
        date_from=req.date_from,
        date_to=req.date_to,
        current_only=req.current_only,
        include_superseded=req.include_superseded,
        limit=max(1, min(req.limit, 200)),
    )


@router.post("/supersede")
def artifact_supersede(req: ArtifactSupersedeRequest):
    try:
        return hermes_artifact_supersede(
            superseded_id=req.superseded_id,
            replacement_id=req.replacement_id,
            notes=req.notes,
            actor_id=req.actor_id,
            actor_type=req.actor_type,
            actor_label=req.actor_label,
            actor_source=req.actor_source,
            approval_method=req.approval_method,
            approval_confidence=req.approval_confidence,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{artifact_id}")
def artifact_get(artifact_id: str):
    result = hermes_artifact_get(artifact_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"artifact not found: {artifact_id}")
    return result


@router.post("/{artifact_id}/status")
def artifact_update_status(artifact_id: str, req: ArtifactUpdateStatusRequest):
    try:
        return hermes_artifact_update_status(
            artifact_id,
            approval_status=req.approval_status,
            notes=req.notes,
            safety_status=req.safety_status,
            actor_id=req.actor_id,
            actor_type=req.actor_type,
            actor_label=req.actor_label,
            actor_source=req.actor_source,
            approval_method=req.approval_method,
            approval_confidence=req.approval_confidence,
            actor_note=req.actor_note,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{artifact_id}/export")
def artifact_export(artifact_id: str, export_format: str = Query(default="json")):
    try:
        return hermes_artifact_export(artifact_id, export_format=export_format)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
