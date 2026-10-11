"""Response scrubber for the family editions (AMP / Maxine).

Family sites must not show Empire internals: git commit/branch/build info,
host names, the owner's repo or data paths, or internal docs file names.
On family editions every JSON response under /api is filtered:

* values of version-control / build / host keys are set to None;
* any token containing an owner path or internal marker is replaced with
  "[oculto]".

No-op on the workroom edition. Streaming and non-JSON responses pass through.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from starlette.responses import Response

_MAX_BYTES = 8 * 1024 * 1024

_SENSITIVE_KEYS = {
    "commit", "commit_hash", "commit_sha", "commit_id", "git_commit", "git_sha",
    "git_hash", "sha", "head", "head_sha", "branch", "git_branch", "current_branch",
    "build_id", "build_sha", "build_time", "build_version", "git", "git_info",
    "hostname", "host_name", "machine", "node_name", "platform_node", "repo",
    "repo_path", "repo_root", "repo_dir", "project_root", "cwd", "uptime_host",
    "empire_version", "app_version", "backend_version", "frontend_version",
    "kernel", "os_release", "tailscale_ip", "tailnet_ip", "lan_ip", "local_ip",
}

# Any key that names version control, build, host, repo or port info.
_SENSITIVE_KEY_RE = re.compile(
    r"commit|branch|(^|_)git($|_)|build_(id|sha|time|version)|worktree|hostname|host_name"
    r"|(^|_)repo($|_)|repo_(path|root|dir)|(^|_)(sha|head_sha)$|(^|_)ports?($|_)|port_observations"
    r"|tailscale|tailnet|(^|_)(lan|local)_ip$|kernel|os_release",
    re.I,
)

_MARKERS = [
    r"localhost:\d+", r"127\.0\.0\.1:\d+", r"0\.0\.0\.0:\d+",
    r"/home/rg", r"~/empire", r"empire-repo", r"empire-box-memory", r"empire-amp",
    r"empire-maxine", r"empire-command-center", r"/data/images", r"\.hermes",
    r"empiredell", r"empire-dell", r"/mnt/", r"/media/", r"docs/recovered",
    r"empire_v\d", r"/data/backups", r"/data/empire", r"openclaw-",
    r"\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b",
    r"\b192\.168\.\d{1,3}\.\d{1,3}\b", r"\.ts\.net\b", r"tail[0-9a-f]{6}",
]


def _edition() -> str:
    return (os.getenv("EMPIRE_EDITION") or "").strip().lower()


def _marker_re() -> re.Pattern:
    ed = _edition()
    other_data = r"/data/(?!%s(?:/|\b))[A-Za-z0-9_.-]+" % re.escape(ed or "amp")
    pat = "|".join(_MARKERS + [other_data])
    return re.compile(r"[^\s\"'`,;()<>\[\]{}]*(?:%s)[^\s\"'`,;()<>\[\]{}]*" % pat, re.I)


_RE = None


def scrub_value(value: Any) -> Any:
    global _RE
    if _RE is None:
        _RE = _marker_re()
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if isinstance(k, str) and (k.lower() in _SENSITIVE_KEYS or _SENSITIVE_KEY_RE.search(k)) and not isinstance(v, bool):
                out[k] = None
            else:
                out[_RE.sub("[oculto]", k) if isinstance(k, str) else k] = scrub_value(v)
        return out
    if isinstance(value, list):
        return [scrub_value(v) for v in value]
    if isinstance(value, str):
        return _RE.sub("[oculto]", value)
    return value


def _rebuild(original, new: bytes) -> Response:
    resp = Response(content=new, status_code=original.status_code,
                    background=getattr(original, "background", None))
    resp.raw_headers = [
        (k, v) for k, v in original.raw_headers if k.lower() != b"content-length"
    ] + [(b"content-length", str(len(new)).encode())]
    return resp


async def scrub_family_response(request, response):
    try:
        path = request.url.path
        if not path.startswith("/api"):
            return response
        ctype = (response.headers.get("content-type") or "").lower()
        if "json" not in ctype:
            return response
        clen = response.headers.get("content-length")
        if clen is not None and int(clen) > _MAX_BYTES:
            return response
        if response.headers.get("content-encoding"):
            return response
        body = b""
        async for chunk in response.body_iterator:
            body += chunk if isinstance(chunk, bytes) else chunk.encode()
            if len(body) > _MAX_BYTES:
                # Too large to scrub safely: refuse rather than leak.
                return Response(status_code=502, content=b'{"detail":"respuesta demasiado grande"}',
                                media_type="application/json")
        try:
            data = json.loads(body)
        except Exception:
            text = body.decode("utf-8", "replace")
            global _RE
            if _RE is None:
                _RE = _marker_re()
            return _rebuild(response, _RE.sub("[oculto]", text).encode())
        return _rebuild(response, json.dumps(scrub_value(data), ensure_ascii=False).encode("utf-8"))
    except Exception:
        return Response(status_code=500, content=b'{"detail":"error interno"}',
                        media_type="application/json")
