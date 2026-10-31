"""Standard job document-set: stages, naming, gates, backfill."""

from app.services.job_stages.catalog import (
    GATE_STAGE_KEY,
    STAGES,
    STAGE_WORKROOM,
    WORKROOM_MARKUP,
)
from app.services.job_stages.gate import (
    ClientEstimateGateError,
    SquareSendGateError,
    assert_client_estimate_allowed,
    assert_share_export_allowed,
    assert_square_send_allowed,
)
from app.services.job_stages.schema import init_job_stages_schema
from app.services.job_stages.service import (
    approve_stage,
    ensure_job_stages,
    get_checklist,
    job_location,
    register_document,
)

__all__ = [
    "GATE_STAGE_KEY",
    "STAGES",
    "STAGE_WORKROOM",
    "WORKROOM_MARKUP",
    "ClientEstimateGateError",
    "SquareSendGateError",
    "assert_client_estimate_allowed",
    "assert_share_export_allowed",
    "assert_square_send_allowed",
    "init_job_stages_schema",
    "approve_stage",
    "ensure_job_stages",
    "get_checklist",
    "job_location",
    "register_document",
]
