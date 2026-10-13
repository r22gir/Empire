"""Open a GitHub issue (label max-improvement) so a Cursor agent can draft a PR.

Never merges. Never deploys. Never pushes to the base branch.
"""
from __future__ import annotations

import os
import re
from typing import Optional
from urllib.parse import urlparse

import httpx

from app.services.max.improve_base_ref import assert_safe_improve_base_ref, resolve_base_ref
from app.services.max.improvements import REPO_URL

LABEL = "max-improvement"
API_ROOT = "https://api.github.com"


class GitHubUnavailable(RuntimeError):
    pass


def github_token() -> str:
    for name in ("MAX_IMPROVE_GITHUB_TOKEN", "GITHUB_TOKEN", "GH_TOKEN"):
        val = (os.getenv(name) or "").strip()
        if val:
            return val
    return ""


def github_configured() -> bool:
    return bool(github_token())


def repo_slug(url: Optional[str] = None) -> tuple[str, str]:
    raw = (url or os.getenv("MAX_IMPROVE_REPO") or REPO_URL or "").strip()
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    parts = [p for p in (parsed.path or "").split("/") if p]
    if len(parts) < 2:
        return "r22gir", "Empire"
    owner, name = parts[0], parts[1]
    if name.endswith(".git"):
        name = name[:-4]
    return owner, name


def _headers() -> dict:
    token = github_token()
    if not token:
        raise GitHubUnavailable("No GitHub token (MAX_IMPROVE_GITHUB_TOKEN / GITHUB_TOKEN)")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "empire-max-improvements",
    }


def _ensure_label(client: httpx.Client, owner: str, name: str) -> None:
    r = client.get(f"{API_ROOT}/repos/{owner}/{name}/labels/{LABEL}", headers=_headers())
    if r.status_code == 200:
        return
    client.post(
        f"{API_ROOT}/repos/{owner}/{name}/labels",
        headers=_headers(),
        json={
            "name": LABEL,
            "color": "6d28d9",
            "description": "Max self-improvement plan for a Cursor cloud agent (draft PR only)",
        },
    )


def issue_body(req: dict, plan: str) -> str:
    BASE_REF = assert_safe_improve_base_ref(resolve_base_ref())
    mods = ", ".join(req.get("affected_modules") or []) or "(see plan)"
    return f"""# IMP-{int(req['id']):04d}: {req.get('title')}

**Do not merge. Do not deploy.** Rafael approves deploys after Chief e review.

This issue is a **draft-PR request** for a Cursor cloud agent (**grok-4.6**) on
`{REPO_URL}` (base `{BASE_REF}`). Open a new `cursor/...` branch and a **draft** pull
request. Never push to `{BASE_REF}`.

## Problem
{req.get('problem') or ''}

## Proposed change
{req.get('proposed_change') or ''}

## Affected modules
{mods}

## Risk
{req.get('risk') or 'medium'}

## Atlas / MiniMax plan
{plan}

## House rules
- Never edit `max/memory.md`. Never touch OpenClaw, test-studio or willard data.
- Never print or commit secrets, `.env`, `client_aliases.json`, or `business.json`.
- Outreach stays draft-only: no email, SMS, WhatsApp, or social posts.
- No amp/maxine code. No live-data writes in tests.
- Keep Dark and Gold themes; check mobile at 390px for UI changes.
- In the PR description list: what changed, how it was tested, screenshots for UI, rollback.

Label: `{LABEL}`
"""


def open_improvement_issue(req: dict, plan: str) -> dict:
    """POST /repos/{owner}/{repo}/issues with label max-improvement."""
    if not github_configured():
        raise GitHubUnavailable("GitHub token not set")
    owner, name = repo_slug()
    title = f"IMP-{int(req['id']):04d}: {req.get('title')}"[:240]
    body = issue_body(req, plan)
    with httpx.Client(timeout=30) as client:
        try:
            _ensure_label(client, owner, name)
        except Exception:
            pass
        r = client.post(
            f"{API_ROOT}/repos/{owner}/{name}/issues",
            headers=_headers(),
            json={"title": title, "body": body, "labels": [LABEL]},
        )
    if r.status_code >= 400:
        raise GitHubUnavailable(f"GitHub HTTP {r.status_code}: {(r.text or '')[:240]}")
    try:
        data = r.json() or {}
    except Exception:
        data = {}
    url = (data or {}).get("html_url") or ""
    number = (data or {}).get("number")
    if not url:
        raise GitHubUnavailable("GitHub issue response had no html_url")
    return {
        "issue_url": url,
        "issue_number": number,
        "title": title,
        "label": LABEL,
        "merged": False,
        "deployed": False,
    }


def parse_issue_number(url: str) -> Optional[int]:
    m = re.search(r"/issues/(\d+)", url or "")
    return int(m.group(1)) if m else None
