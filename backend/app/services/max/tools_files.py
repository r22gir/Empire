"""Max file tools: find_files (search Rafael's files) and share_file (to Rafael only).

Registered into tool_executor.TOOL_REGISTRY on import (imported at the end of
tool_executor.py, same pattern as tools_acquisition). Search logic and the
exclusion rules live in file_finder.py.

Rules enforced here, not in the prompt:
- read-only: nothing is moved, renamed, edited or deleted; email/WhatsApp
  attach a temp copy so no tool can write next to the original;
- share_file only reaches Rafael himself (Studio chat link, his own email
  addresses, his WhatsApp). Anyone else is refused; that needs his explicit
  yes through the normal client-send path;
- every "found"/"sent" claim is backed by this tool's result.
"""
from __future__ import annotations

import asyncio
import mimetypes
import os
import shutil
import tempfile
from typing import Optional

from app.services.max.tool_executor import ToolResult, tool
from app.services.max import file_finder as ff

SHARE_VIAS = ("studio", "email", "whatsapp")


def _run_async(coro, timeout: int = 120):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result(timeout=timeout)


@tool("find_files")
def _find_files(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Search Rafael's files on the Dell by name, client/alias, quote number. Read-only."""
    q = " ".join(str(params.get(k) or "").strip() for k in ("query", "q", "name", "client", "quote_number")).strip()
    if not q:
        return ToolResult(tool="find_files", success=False,
                          error="Say what to look for: a file name, client, nickname or quote number.")
    try:
        limit = int(params.get("limit") or 15)
    except (TypeError, ValueError):
        limit = 15
    res = ff.find_files(q, limit=limit)
    if res.get("error") and not res.get("found"):
        return ToolResult(tool="find_files", success=False, error=res["error"], result=res)
    if not res.get("found"):
        near = "; ".join(c["path"] for c in res.get("closest") or [])
        return ToolResult(tool="find_files", success=False, result=res, error=(
            f'No file matched "{q}". ' + (f"Closest names: {near}. " if near else "No close names either. ")
            + "Say so plainly; do not present any file as found."))
    res["message"] = (f"{res['total']} match(es) for \"{q}\", best first"
                      + (f" (showing {len(res['matches'])})" if res['total'] > len(res['matches']) else "")
                      + ". Use share_file with a file_id to show or send one to Rafael.")
    if res.get("indexing"):
        res["message"] += " Still indexing: " + ", ".join(res["indexing"]) + " (results there may be missing)."
    return ToolResult(tool="find_files", success=True, result=res)


def _temp_copy(path: str) -> str:
    d = tempfile.mkdtemp(prefix="max-share-")
    dst = os.path.join(d, os.path.basename(path))
    shutil.copyfile(path, dst)
    return dst


def _founder_whatsapp() -> Optional[str]:
    try:
        from app.services.max.whatsapp_channel import founder_allowlist
        nums = sorted(founder_allowlist())
        return nums[0] if nums else None
    except Exception:
        return None


async def _send_whatsapp_file(to: str, path: str, caption: str) -> dict:
    from app.services.max import whatsapp_channel as wa
    wa._require_enabled()
    if not wa.is_allowlisted(to):
        raise wa.WhatsAppSendBlocked("recipient is not Rafael's number")
    if not wa.customer_window_open(to):
        raise wa.WhatsAppSendBlocked("WhatsApp 24-hour window is closed; Rafael must message Max first")
    data = ff.read_file_bytes(path)
    name = os.path.basename(path)[:120]
    mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
    media_id = await wa.upload_media(data, mime, name)
    graph = await wa._post_graph({
        "messaging_product": "whatsapp", "recipient_type": "individual", "to": wa.normalize_msisdn(to),
        "type": "document", "document": {"id": media_id, "filename": name, "caption": caption[:1024]},
    })
    return {"media_id": media_id, "filename": name, "graph_ok": bool(graph)}


@tool("share_file")
def _share_file(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Show or send a found file to Rafael: studio link, his own email, or his WhatsApp."""
    ref = str(params.get("file_id") or params.get("path") or params.get("file") or "").strip()
    via = str(params.get("via") or params.get("channel") or "studio").strip().lower()
    if via in ("chat", "web", "link", "view", "open"):
        via = "studio"
    if via in ("mail", "gmail"):
        via = "email"
    if via in ("wa", "whats app"):
        via = "whatsapp"
    if via not in SHARE_VIAS:
        return ToolResult(tool="share_file", success=False, error=f"via must be one of {', '.join(SHARE_VIAS)}")
    path = ff.resolve_file(ref)
    if not path:
        return ToolResult(tool="share_file", success=False, error=(
            "That file is not available: run find_files first and pass its file_id. Protected files "
            "(credentials, databases, family-edition data) are never shared."))
    name = os.path.basename(path)
    shown = ff._display_path(path)
    size = os.path.getsize(path)
    if via == "studio":
        token = ff.share_token(path)
        url = f"/api/v1/files/found?t={token}"
        return ToolResult(tool="share_file", success=True, result={
            "action": "open_file", "via": "studio", "name": name, "path": shown, "size": ff._human_size(size),
            "viewer_url": url, "download_url": url + "&download=1", "expires_in_hours": 24,
            "message": f"[{name}]({url}) — {shown} ({ff._human_size(size)}). Link works for 24 hours.",
        })
    if via == "email":
        from app.services.max.email_recipient_whitelist import is_founder_self_email, FOUNDER_SELF_EMAILS
        to = str(params.get("to") or "").strip()
        if to.lower() in ("", "me", "myself", "rafael", "founder", "owner", "my email"):
            to = os.getenv("FOUNDER_EMAIL", "empirebox2026@gmail.com")
        if not is_founder_self_email(to):
            return ToolResult(tool="share_file", success=False, error=(
                "share_file only emails Rafael's own addresses (" + ", ".join(sorted(FOUNDER_SELF_EMAILS))
                + "). Sending to anyone else needs his explicit yes first."))
        if size > 20 * 1024 * 1024:
            return ToolResult(tool="share_file", success=False,
                              error=f"{name} is {ff._human_size(size)}; too large for email (20 MB max). Offer the Studio link.")
        from app.services.max.tool_executor import execute_tool
        copy = _temp_copy(path)
        try:
            res = execute_tool({"tool": "send_email", "to": to, "subject": str(params.get("subject") or f"File: {name}"),
                                "body": str(params.get("body") or f"Attached: {name}\nFrom: {shown}"),
                                "attachments": [copy]}, founder=False, channel="share_file")
        finally:
            shutil.rmtree(os.path.dirname(copy), ignore_errors=True)
        data = res.to_dict()
        if not data.get("success"):
            return ToolResult(tool="share_file", success=False, error=f"Email not sent: {data.get('error')}")
        r = data.get("result") or {}
        return ToolResult(tool="share_file", success=True, result={
            "via": "email", "name": name, "path": shown, "sent_to": r.get("sent_to") or to,
            "message_id": r.get("message_id"), "attachments_sent": r.get("attachments_sent"),
            "message": f"Emailed {name} to {to}."})
    # whatsapp
    to = _founder_whatsapp()
    if not to:
        return ToolResult(tool="share_file", success=False, error="Rafael's WhatsApp number is not on file.")
    try:
        sent = _run_async(_send_whatsapp_file(to, path, str(params.get("caption") or f"{name} — for you")))
    except Exception as exc:
        return ToolResult(tool="share_file", success=False, error=f"WhatsApp not sent: {str(exc)[:200]}")
    return ToolResult(tool="share_file", success=True, result={
        "via": "whatsapp", "name": name, "path": shown, "media_id": sent.get("media_id"),
        "message": f"Sent {name} to Rafael on WhatsApp."})


FILE_TOOLS_DOC = """
### Rafael's files (read-only search + share to Rafael)
- **find_files** — Search ALL of Rafael's files on the Dell (home folders: jobs, empire-data, Downloads, Desktop,
  Documents, Pictures, quote/invoice PDFs, plus mounted drives like the BACKUP1 USB) by file name, client or
  nickname (Dahlia = Nehal Elrefai), quote number or words in the name. Returns EVERY match ranked (finals and
  newest first) with a file_id each. Use it whenever he asks for a file, doc, PDF, photo or "find X".
  Credentials, databases and family-edition (AMP/Maxine) data are never searchable.
  `{"tool": "find_files", "query": "Nehal final estimate"}`
- **share_file** — Show or send one found file to Rafael: via "studio" (chat link, 24 h), "email" (his own
  addresses only, sent right away) or "whatsapp" (his number). Never to anyone else.
  `{"tool": "share_file", "file_id": "<from find_files>", "via": "studio"}`
- List ALL relevant matches (e.g. both Nehal phases), not just the first. Never say you found or sent a file
  without a successful find_files / share_file result. If nothing matched, say so and name the closest files.
"""

try:
    ff.warm_index_async()
except Exception:
    pass
