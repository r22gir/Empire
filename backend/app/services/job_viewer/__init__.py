"""Max 3D Job Viewer — generate a self-contained HTML scene from a job or quote.

Preview is always a draft. Publish is founder-tap only and never runs
automatically. Client-facing HTML is Empire Workroom branded and strips
supplier names, SKUs, prices, and addresses.
"""

from app.services.job_viewer.service import (
    JobViewerError,
    PublishNotConfigured,
    ViewerForbidden,
    get_viewer_status,
    preview_from_job,
    preview_from_payload,
    preview_from_quote,
    publish_viewer,
    unpublish_viewer,
)

__all__ = [
    "JobViewerError",
    "PublishNotConfigured",
    "ViewerForbidden",
    "get_viewer_status",
    "preview_from_job",
    "preview_from_payload",
    "preview_from_quote",
    "publish_viewer",
    "unpublish_viewer",
]
