"""
Max client-acquisition tools (LeadForge / SocialForge / pipeline) + module bridge.

Registered into tool_executor.TOOL_REGISTRY on import (imported at the end of
tool_executor.py). Guide: docs/MAX_PROSPECTING.md.

Hard rule for every tool here: outreach is DRAFT-ONLY. Nothing in this file can
send an email, DM, SMS or post. Max must ask Rafael before any send, and sending
stays a separate, existing, founder-gated step.
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Optional

from app.services.max.tool_executor import ToolResult, tool

_DRAFT_POLICY = "Draft only. Nothing was sent. Ask Rafael before any send."


def _run_async(coro, timeout: int = 600):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result(timeout=timeout)


def _ids(params: dict) -> list:
    raw = params.get("prospect_ids") or params.get("ids") or params.get("prospect_id") or []
    if isinstance(raw, (int, str)):
        raw = [raw]
    out = []
    for x in raw:
        try:
            out.append(int(x))
        except (TypeError, ValueError):
            continue
    return out


def _err(name: str, e: Exception) -> ToolResult:
    return ToolResult(tool=name, success=False, error=f"{type(e).__name__}: {str(e)[:300]}")


@tool("prospect_search")
def _prospect_search(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Run a real LeadForge prospect search (Brave + Google Places + Yelp when keys exist)."""
    try:
        from app.services.leadforge.prospect_engine import run_prospect_search
        from app.services.leadforge import prospect_ops as po
        res = _run_async(run_prospect_search(params.get("business_unit") or "workroom",
                                             params.get("location") or "DMV",
                                             params.get("target_type") or "interior designers"))
        if not res.get("success"):
            return ToolResult(tool="prospect_search", success=False, error=res.get("error") or "search failed")
        top = [po.card(p) for p in po._ranked(res.get("top_prospects") or [])][:10]
        return ToolResult(tool="prospect_search", success=True, result={
            "search_run_id": res["search_run_id"], "raw": res["raw_result_count"], "unique": res["unique_result_count"],
            "new": res["inserted_count"], "already_known": res["deduped_count"],
            "providers_succeeded": res["providers_succeeded"], "providers_failed": res["providers_failed"],
            "top_new": top, "next": "prospect_enrich on the best ids, then prospect_rank."})
    except Exception as e:
        return _err("prospect_search", e)


@tool("prospect_enrich")
def _prospect_enrich(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Free contact lookup on prospects' own websites (robots.txt, rate limited, max 25/call)."""
    try:
        from app.services.leadforge.contact_enrich import enrich_prospects
        from app.services.leadforge.prospect_ops import top_prospects
        ids = _ids(params)
        if not ids:
            ids = [p["id"] for p in top_prospects(limit=int(params.get("top_n") or 10),
                                                  min_score=int(params.get("min_score") or 0),
                                                  exclude_pipeline=bool(params.get("exclude_pipeline", True)))
                   if not p.get("is_directory_page")]
        res = _run_async(enrich_prospects(ids, force=bool(params.get("force")),
                                          discover_websites=bool(params.get("discover_websites"))))
        return ToolResult(tool="prospect_enrich", success=True, result=res)
    except Exception as e:
        return _err("prospect_enrich", e)


@tool("prospect_rank")
def _prospect_rank(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Score/rank prospects: listing score + reachability (named contact, email, Instagram, fit)."""
    try:
        from app.services.leadforge import prospect_ops as po
        rows = po.top_prospects(limit=int(params.get("limit") or 10), min_score=int(params.get("min_score") or 0),
                                only_new=bool(params.get("only_new")), days=params.get("days"),
                                exclude_pipeline=bool(params.get("exclude_pipeline")))
        return ToolResult(tool="prospect_rank", success=True, result={"prospects": [po.card(p) for p in rows]})
    except Exception as e:
        return _err("prospect_rank", e)


@tool("prospect_add_to_pipeline")
def _prospect_add_to_pipeline(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Add prospects to the pipeline AND create their LeadForge leads (with a 2-day first-contact reminder)."""
    try:
        from app.services.leadforge import prospect_ops as po
        ids = _ids(params)
        if not ids and params.get("top_n"):
            ids = [p["id"] for p in po.top_prospects(limit=int(params["top_n"]), exclude_pipeline=True,
                                                     min_score=int(params.get("min_score") or 0))
                   if not p.get("is_directory_page")]
        if not ids:
            return ToolResult(tool="prospect_add_to_pipeline", success=False, error="Give prospect_ids or top_n")
        out = [po.promote_to_lead(i, business_unit=params.get("business_unit")) for i in ids[:25]]
        return ToolResult(tool="prospect_add_to_pipeline", success=True, result={"results": out})
    except Exception as e:
        return _err("prospect_add_to_pipeline", e)


@tool("prospect_draft_outreach")
def _prospect_draft_outreach(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Save an outreach DRAFT (email or instagram_dm) for one or more prospects. Never sends."""
    try:
        from app.services.leadforge.prospect_ops import draft_outreach
        ids = _ids(params)
        if not ids:
            return ToolResult(tool="prospect_draft_outreach", success=False, error="prospect_id required")
        ch = (params.get("channel") or "email").lower()
        drafts = [draft_outreach(i, channel=ch) for i in ids[:10]]
        return ToolResult(tool="prospect_draft_outreach", success=True,
                          result={"drafts": drafts, "send_policy": _DRAFT_POLICY})
    except Exception as e:
        return _err("prospect_draft_outreach", e)


@tool("prospect_daily_brief")
def _prospect_daily_brief(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Top 5-10 new prospects (who, why, suggested first message) + today's pipeline reminders."""
    try:
        from app.services.leadforge.prospect_ops import daily_brief
        from app.services.leadforge.acquisition import followups_due
        brief = daily_brief(limit=int(params.get("limit") or 7), days=int(params.get("days") or 1))
        fu = followups_due(days_ahead=0)
        brief["pipeline_reminders"] = {"overdue": fu["overdue"][:10], "due_today": fu["due_today"][:10],
                                       "quotes_waiting": fu["quotes_waiting"][:5], "counts": fu["counts"]}
        brief["send_policy"] = _DRAFT_POLICY
        return ToolResult(tool="prospect_daily_brief", success=True, result=brief)
    except Exception as e:
        return _err("prospect_daily_brief", e)


@tool("prospect_segments")
def _prospect_segments(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Pipeline/prospect segments (designers, has_email, has_instagram, ...; combine with +)."""
    try:
        from app.services.leadforge import prospect_ops as po
        name = params.get("segment") or params.get("name")
        inp = bool(params.get("in_pipeline_only"))
        res = po.segment_members(name, in_pipeline_only=inp, limit=int(params.get("limit") or 50)) if name \
            else po.segments(in_pipeline_only=inp)
        if res.get("error"):
            return ToolResult(tool="prospect_segments", success=False, error=res["error"])
        return ToolResult(tool="prospect_segments", success=True, result=res)
    except Exception as e:
        return _err("prospect_segments", e)


@tool("prospect_social_targets")
def _prospect_social_targets(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Prospects with Instagram/Facebook/LinkedIn (feeds SocialForge engage list)."""
    try:
        from app.services.leadforge.prospect_ops import social_targets
        return ToolResult(tool="prospect_social_targets", success=True,
                          result=social_targets(limit=int(params.get("limit") or 50)))
    except Exception as e:
        return _err("prospect_social_targets", e)


@tool("pipeline_followups")
def _pipeline_followups(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Follow-up reminders: overdue/today/upcoming lead actions, never-contacted leads, sent quotes waiting."""
    try:
        from app.services.leadforge.acquisition import followups_due
        return ToolResult(tool="pipeline_followups", success=True,
                          result=followups_due(days_ahead=int(params.get("days_ahead") or 7),
                                               stale_days=int(params.get("stale_days") or 5)))
    except Exception as e:
        return _err("pipeline_followups", e)


@tool("set_followup")
def _set_followup(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Put a follow-up reminder on a pipeline lead: lead_id + when (YYYY-MM-DD) or in_days, action."""
    try:
        from app.services.leadforge.acquisition import set_followup
        if not params.get("lead_id"):
            return ToolResult(tool="set_followup", success=False, error="lead_id required")
        out = set_followup(int(params["lead_id"]), when=params.get("when"), in_days=params.get("in_days"),
                           action=params.get("action"))
        if out.get("error"):
            return ToolResult(tool="set_followup", success=False, error=out["error"])
        return ToolResult(tool="set_followup", success=True, result=out)
    except Exception as e:
        return _err("set_followup", e)


@tool("reactivation_list")
def _reactivation_list(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Past paying clients, accepted-quote clients and designers gone quiet + suggested message (text only)."""
    try:
        from app.services.leadforge.acquisition import reactivation_list
        return ToolResult(tool="reactivation_list", success=True, result=reactivation_list(
            months_quiet=int(params.get("months_quiet") or 6), limit=int(params.get("limit") or 25),
            include_designers=bool(params.get("include_designers", True))))
    except Exception as e:
        return _err("reactivation_list", e)


@tool("socialforge_draft_post")
def _socialforge_draft_post(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Save a SocialForge post as a DRAFT (social proof: finished job, before/after, designer shout-out).
    Status is forced to 'draft'; publishing stays a manual SocialForge step."""
    try:
        import httpx
        content = (params.get("content") or "").strip()
        if not content:
            return ToolResult(tool="socialforge_draft_post", success=False, error="content required (write the caption)")
        body = {"platform": (params.get("platform") or "instagram").lower(), "content": content,
                "hashtags": params.get("hashtags") or "", "media_url": params.get("media_url"),
                "campaign_id": params.get("campaign_id"), "status": "draft"}
        with httpx.Client(timeout=20) as c:
            r = c.post(f"{_API}/api/v1/socialforge/posts", json=body)
        if r.status_code >= 400:
            return ToolResult(tool="socialforge_draft_post", success=False, error=f"HTTP {r.status_code} {r.text[:200]}")
        post = r.json()
        queue_id = None
        try:
            from app.services.leadforge import growth
            queue_id = growth.enqueue(channel="social", kind="social_post", source="socialforge", source_ref=post.get("id"),
                                      body=f"{content}\n\n{body['hashtags']}".strip(), media_urls=[body["media_url"]] if body.get("media_url") else [],
                                      title=f"{body['platform'].title()} post draft", created_by="max")["id"]
        except Exception:
            pass
        return ToolResult(tool="socialforge_draft_post", success=True,
                          result={"post": post, "approval_queue_id": queue_id,
                                  "send_policy": "Draft only. Not posted. It is in the Approvals queue; Rafael copies and posts."})
    except Exception as e:
        return _err("socialforge_draft_post", e)


# ── Growth: approval queue, deposits, ROI, social proof, Place Details, improvements ──

@tool("approval_queue")
def _approval_queue(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Read the one approval queue (every draft waiting for Rafael's tap). Read-only."""
    try:
        from app.services.leadforge import growth
        q = growth.list_queue(params.get("status") or "pending", int(params.get("limit") or 50))
        items = [{k: i.get(k) for k in ("id", "kind", "channel", "title", "to_name", "to_address", "subject", "status", "created_at")}
                 for i in q["items"]]
        return ToolResult(tool="approval_queue", success=True,
                          result={"items": items, "counts": q["counts"], "policy": q["policy"],
                                  "how_rafael_approves": "Studio → LeadForge → Approvals. Max cannot approve or send."})
    except Exception as e:
        return _err("approval_queue", e)


@tool("draft_followup")
def _draft_followup(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Put a follow-up / reactivation message in the approval queue (email, sms or instagram). Never sends."""
    try:
        from app.services.leadforge import growth
        body = (params.get("body") or params.get("message") or "").strip()
        if not body:
            return ToolResult(tool="draft_followup", success=False, error="body required (write the message)")
        lead_id = params.get("lead_id")
        to_name, to_addr = params.get("to_name") or "", params.get("to_address") or params.get("to") or ""
        channel = (params.get("channel") or "email").lower()
        if lead_id and not to_addr:
            with growth._db() as conn:
                r = conn.execute("SELECT * FROM lf_leads WHERE id=?", (int(lead_id),)).fetchone()
            if r:
                to_name = to_name or " ".join(x for x in (r["first_name"], r["last_name"]) if x) or (r["company"] or "")
                to_addr = (r["email"] if channel == "email" else r["phone"] if channel == "sms" else "") or ""
        item = growth.enqueue(channel=channel, kind="followup", body=body, source="max_followup",
                              title=params.get("title") or f"Follow-up to {to_name or to_addr or 'contact'}",
                              to_name=to_name, to_address=to_addr, subject=params.get("subject") or "",
                              lead_id=int(lead_id) if lead_id else None, customer_id=params.get("customer_id"))
        return ToolResult(tool="draft_followup", success=True,
                          result={"approval_queue_id": item["id"], "channel": item["channel"], "to": to_addr or None,
                                  "missing_address": not to_addr, "send_policy": _DRAFT_POLICY + " It is in the Approvals queue."})
    except Exception as e:
        return _err("draft_followup", e)


@tool("reconcile_deposits")
def _reconcile_deposits(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Mark leads won for every paid deposit/invoice (idempotent). Internal data only."""
    try:
        from app.services.leadforge import growth
        return ToolResult(tool="reconcile_deposits", success=True, result=growth.reconcile_paid_deposits())
    except Exception as e:
        return _err("reconcile_deposits", e)


@tool("roi_report")
def _roi_report(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Lead source -> quotes -> paid invoices, with manual spend per channel. Read-only."""
    try:
        from app.services.leadforge import growth
        return ToolResult(tool="roi_report", success=True, result=growth.roi_report(int(params.get("months") or 12)))
    except Exception as e:
        return _err("roi_report", e)


@tool("social_proof_drafts")
def _social_proof_drafts(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Finished job -> before/after SocialForge post drafts (+ approval queue). {job_id} or {scan: true}. Never posts."""
    try:
        from app.services.leadforge import growth
        if params.get("job_id"):
            res = growth.social_proof_for_job(str(params["job_id"]), bool(params.get("force")))
        else:
            res = growth.scan_completed_jobs(int(params.get("days") or 30))
        return ToolResult(tool="social_proof_drafts", success=True, result=res)
    except Exception as e:
        return _err("social_proof_drafts", e)


@tool("place_details_enrich")
def _place_details_enrich(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Google Place Details (website + phone) for Google prospects. Max stays inside the free 1,000 calls/month."""
    try:
        from app.services.leadforge import place_details
        ids = _ids(params)
        res = place_details.enrich(int(params.get("limit") or 25), ids or None, allow_paid=False)
        res.pop("results", None) if len(res.get("results") or []) > 30 else None
        return ToolResult(tool="place_details_enrich", success=res.get("status") not in ("needs_key",), result=res,
                          error="GOOGLE_PLACES_API_KEY not configured" if res.get("status") == "needs_key" else None)
    except Exception as e:
        return _err("place_details_enrich", e)


@tool("request_improvement")
def _request_improvement(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Write a structured change request for Rafael (Improvements page). Max never edits code or deploys."""
    try:
        from app.services.max import improvements as imp
        req = imp.create_request(
            title=params.get("title") or "", problem=params.get("problem") or "",
            proposed_change=params.get("proposed_change") or params.get("change") or "",
            affected_modules=params.get("affected_modules") or [], risk=params.get("risk") or "medium",
            acceptance=params.get("acceptance") or "", requested_via=params.get("requested_via") or "chat",
            requested_text=params.get("requested_text") or "")
        return ToolResult(tool="request_improvement", success=True, result={
            "id": req["id"], "title": req["title"], "status": req["status"], "risk": req["risk"],
            "next_step": "Rafael reviews it in Studio → Improvements and taps Approve to start the build. "
                         "Nothing is built, merged or deployed before that, and merge needs a second approval."})
    except Exception as e:
        return _err("request_improvement", e)


@tool("improvements_list")
def _improvements_list(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Read the Improvements queue (status, PR / preview links). Read-only."""
    try:
        from app.services.max import improvements as imp
        data = imp.list_requests(params.get("status"))
        items = [{k: i.get(k) for k in ("id", "title", "status", "risk", "pr_url", "preview_url", "spec_path", "next_step")}
                 for i in data["items"][:30]]
        return ToolResult(tool="improvements_list", success=True,
                          result={"items": items, "cursor_configured": data["cursor_configured"], "policy": data["policy"]})
    except Exception as e:
        return _err("improvements_list", e)


# ── Module bridge: every backend module, read-only ───────────────────────

_API = "http://127.0.0.1:8000"
_BLOCK = re.compile(r"(send|sync|execute|delete|remove|connect(?!ed)|oauth|callback|webhook|checkout|charge|"
                    r"pay(?!ment)|token|secret|password|(?<![a-z])env(?![a-z])|shell|restart|deploy|backup|restore|"
                    r"export-all|login|(?<![a-z])pin(?![a-z]))", re.I)
_openapi_cache: dict = {}


def _openapi() -> dict:
    if not _openapi_cache:
        import httpx
        with httpx.Client(timeout=20) as c:
            _openapi_cache.update(c.get(f"{_API}/openapi.json").json())
    return _openapi_cache


def _module_of(path: str) -> str:
    bits = path.split("/")
    return bits[3] if path.startswith("/api/v1/") and len(bits) > 3 else bits[1]


@tool("module_catalog")
def _module_catalog(params: dict, desk: Optional[str] = None) -> ToolResult:
    """List backend modules, or the readable GET endpoints of one module (from live OpenAPI)."""
    try:
        paths = _openapi().get("paths", {})
        module = (params.get("module") or "").strip().lower()
        search = (params.get("search") or "").strip().lower()
        if not module and not search:
            counts: dict = {}
            for p, ops in paths.items():
                if "get" in ops and not _BLOCK.search(p):
                    m = _module_of(p)
                    counts[m] = counts.get(m, 0) + 1
            return ToolResult(tool="module_catalog", success=True, result={
                "modules": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
                "how": "module_catalog {module:'leads'} for endpoints, then module_call {path:'/leads/...'}"})
        eps = []
        for p, ops in paths.items():
            if "get" not in ops or _BLOCK.search(p):
                continue
            if module and _module_of(p) != module:
                continue
            summary = (ops["get"].get("summary") or "")
            if search and search not in p.lower() and search not in summary.lower():
                continue
            eps.append({"path": p.replace("/api/v1", "", 1), "summary": summary[:120]})
        return ToolResult(tool="module_catalog", success=True, result={"endpoints": eps[:120], "count": len(eps)})
    except Exception as e:
        return _err("module_catalog", e)


@tool("module_call")
def _module_call(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Read-only GET to any backend module endpoint (e.g. /socialforge/dashboard, /vendorops/...).
    Writes, sends, payments and secrets are blocked; use the dedicated tools for actions."""
    try:
        import httpx
        path = "/" + str(params.get("path") or "").lstrip("/")
        if not path.strip("/"):
            return ToolResult(tool="module_call", success=False, error="path required, e.g. /leads/leadforge/brief")
        full = path if path.startswith("/api/") else "/api/v1" + path
        if _BLOCK.search(full.split("?")[0]) or ".." in full:
            return ToolResult(tool="module_call", success=False,
                              error="Blocked: module_call is read-only and skips send/pay/secret/admin paths.")
        q = params.get("query") or params.get("params") or {}
        with httpx.Client(timeout=30) as c:
            r = c.get(_API + full, params=q if isinstance(q, dict) else None)
        try:
            body = r.json()
        except Exception:
            body = r.text
        text = json.dumps(body, default=str)
        truncated = len(text) > 8000
        return ToolResult(tool="module_call", success=r.status_code < 400, result={
            "status": r.status_code, "path": full, "truncated": truncated,
            "data": json.loads(text[:8000]) if not truncated else text[:8000]},
            error=None if r.status_code < 400 else f"HTTP {r.status_code}")
    except Exception as e:
        return _err("module_call", e)


ACQUISITION_TOOLS_DOC = """
### Client Acquisition (LeadForge / SocialForge / pipeline): DRAFT-ONLY, ask Rafael before any send
- **prospect_search** `{"tool": "prospect_search", "location": "DMV", "target_type": "interior designers", "business_unit": "workroom"}`
- **prospect_enrich** free website contact lookup (owner/principal, email, phone, Instagram; robots.txt respected) `{"tool": "prospect_enrich", "top_n": 10}` or `{"prospect_ids": [352], "discover_websites": true}` (discover = 1 Brave query per prospect without a site, max 10)
- **prospect_rank** score by fit + reachability `{"tool": "prospect_rank", "limit": 10, "exclude_pipeline": true}`
- **prospect_add_to_pipeline** pipeline + LeadForge lead + 2-day first-contact reminder `{"tool": "prospect_add_to_pipeline", "prospect_ids": [352]}` (or `top_n`)
- **prospect_draft_outreach** saves a DRAFT `{"tool": "prospect_draft_outreach", "prospect_id": 352, "channel": "email|instagram_dm"}`
- **prospect_daily_brief** top 5-10 new prospects: who, why, first message + today's reminders `{"tool": "prospect_daily_brief", "limit": 7}`
- **prospect_segments** `{"tool": "prospect_segments", "segment": "designers+has_email", "in_pipeline_only": true}`
- **prospect_social_targets** Instagram/Facebook/LinkedIn list for SocialForge `{"tool": "prospect_social_targets"}`
- **pipeline_followups** overdue/today/upcoming follow-ups, never-contacted leads, sent quotes waiting `{"tool": "pipeline_followups"}`
- **set_followup** `{"tool": "set_followup", "lead_id": 8, "in_days": 3, "action": "Call about samples"}`
- **reactivation_list** past paying clients + designers gone quiet, suggested text `{"tool": "reactivation_list", "months_quiet": 6}`
- **socialforge_draft_post** save a social-proof post as a DRAFT (never published) `{"tool": "socialforge_draft_post", "platform": "instagram", "content": "...", "media_url": "..."}`
- **approval_queue** read the one queue of drafts waiting for Rafael's tap (Max cannot approve)
- **draft_followup** put a follow-up / reactivation message in the queue `{"tool": "draft_followup", "lead_id": 12, "channel": "email", "subject": "...", "body": "..."}`
- **reconcile_deposits** mark leads won for paid deposits (idempotent)
- **roi_report** lead source → quotes → paid invoices, with manual spend per channel
- **social_proof_drafts** finished job → before/after SocialForge drafts `{"job_id": "..."}` or `{"scan": true}`
- **place_details_enrich** Google website + phone for Google prospects (free tier only for Max)
- **request_improvement** write a change request (title, problem, proposed_change, affected_modules, risk, acceptance) for the Improvements page. Use when Rafael asks for a system improvement. Max never edits his own code, never builds, merges or deploys.
- **improvements_list** read the Improvements queue and PR / preview links
- **module_catalog** / **module_call** read-only access to every backend module (live OpenAPI) `{"tool": "module_call", "path": "/socialforge/dashboard"}`
Never send. Show Rafael the draft and wait for an explicit yes; sending stays the existing founder-gated step.
"""
