#!/usr/bin/env python3
"""Run the Max regression set on a TEST COPY of the data (never live).

    cd <checkout>/backend
    TMPDIR=/tmp venv/bin/python tests/max_regression/run_eval.py \
        --snapshot /path/to/snapshot --run-dir /path/to/run-baseline --label baseline

--snapshot must contain data/ (a copy of ~/empire-data made with sqlite backup).
Each run copies it fresh into --run-dir/data, so runs never share writes.

Isolation (same firewall as the pytest suite, tests/_live_data_guard.py):
  * every data env var points at --run-dir (EMPIRE_DATA_DIR, EMPIRE_TASK_DB, ...),
  * an audit hook refuses any open/sqlite/mkdir of ~/empire-data, /data/amp,
    /data/maxine and the live checkout's backend/data + max/memory.md, and TCP to
    the live services (8000, 3005, ...),
  * outbound sends are impossible: SMTP ports and the WhatsApp / Telegram / Gmail
    API hosts are refused, no SMTP/WhatsApp/Telegram/Gmail credentials are loaded,
    and send/share tools are intercepted before the executor (sends to Rafael's own
    addresses return a stand-in success so the reply can be scored; anything else
    is refused),
  * shell / file-write / git / service tools are refused.
Only the model provider settings (and the web search key) are loaded, and never printed.
"""
from __future__ import annotations

import argparse
import asyncio
import contextvars
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parents[1]
TESTS = BACKEND / "tests"
HOME = Path.home()
LIVE_CHECKOUT = Path(os.environ.get("EMPIRE_LIVE_CHECKOUT", str(HOME / "empire-repo-main")))

_ENV_OK = re.compile(
    r"^(?:MINIMAX_[A-Z_]+|MAX_(?:PRIMARY_PROVIDER|DEFAULT_MODEL|DISABLE_[A-Z]+|ALLOW_FALLBACK|FORCE_SINGLE_MODEL|EMAIL|"
    r"EMAIL_ALLOWED_RECIPIENTS|EMAIL_ALLOWED_SENDERS)|BRAVE_API_KEY|FOUNDER_EMAILS?|FOUNDER_ACCESS_EMAILS|EMPIRE_LANE|"
    r"CODE_TASK_MODEL|OPENCLAW_QUARANTINE(?:_LOCK)?|WORKROOM_EMAIL|WOODCRAFT_EMAIL)$")
_ENV_DROP = re.compile(r"^(?:SMTP_|WHATSAPP_|TELEGRAM_|GMAIL_|SENDGRID|META_|FOUNDER_PIN|FOUNDER_APPROVAL_PIN|STRIPE_|"
                       r"XAI_|OPENAI_|ANTHROPIC_|GROQ_|CRYPTO_|EMPIRE_VAULT|CURSOR_API)")
SELF_ADDRESSES = {"empirebox2026@gmail.com", "rafa22giraldo@gmail.com", "max@empirebox.store"}
SEND_TOOLS = {"send_email", "send_quote_email", "share_file", "send_telegram", "send_whatsapp", "send_sms",
              "whatsapp_send", "send_message", "email_quote", "send_invoice_email", "send_document"}
DENY_TOOLS = {"shell_execute", "file_write", "file_edit", "file_append", "file_delete", "git_ops", "service_manager",
              "env_set", "approve_quote", "reject_quote", "deposit_pay_link", "delete_quote", "delete_contact",
              "run_desk_task", "run_code_task", "code_task", "restart_service", "test_runner"}
BLOCKED_HOSTS = ("graph.facebook.com", "api.telegram.org", "gmail.googleapis.com", "oauth2.googleapis.com",
                 "www.googleapis.com", "smtp.gmail.com", "api.sendgrid.com")
SMTP_PORTS = {25, 465, 587, 2525}
LLM_HINT = re.compile(r"minimax|grok|claude|gpt|gemini|deepseek|ollama|groq|llama", re.I)
SHORTCUT_NAMES = {"max-status": "max_status", "whats-new-summary": "whats_new",
                  "empire-runtime-truth-check": "runtime_truth", "clarification-gate": "inventory_clarify",
                  "image-availability-check": "image_unavailable", "attachment-availability-check": "attachment_unavailable",
                  "email-truth-guardrail": "email_guard", "live-lookup-router": "live_lookup",
                  "empire-module-knowledge": "module_knowledge", "gpu-safety-guardrail": "gpu_guard",
                  "guardrail": "input_guard", "attachment-reader": "attachment_reader"}

_PROVIDER_FAIL = re.compile(r"failed and fallback is disabled|Max chat failed|SSLError|provider .* failed", re.I)
REC: contextvars.ContextVar[list | None] = contextvars.ContextVar("max_reg_rec", default=None)
SEND_LOG: list[dict] = []


def _note(item: str) -> None:
    rec = REC.get()
    if rec is not None:
        rec.append(item)


def load_model_env() -> int:
    """Model + search settings only, from the backend's own env file and unit. Values never printed."""
    for name in list(os.environ):
        if _ENV_DROP.match(name):
            os.environ.pop(name, None)
    loaded = 0
    env_file = HOME / ".config" / "empirebox" / "empire-backend.env"
    pairs: list[tuple[str, str]] = []
    try:
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                pairs.append((k.strip().removeprefix("export ").strip(), v.strip().strip('"').strip("'")))
    except OSError:
        pass
    try:
        out = subprocess.run(["systemctl", "--user", "show", "empire-backend", "-p", "Environment", "--value"],
                             capture_output=True, text=True, timeout=10).stdout
        for tok in out.split():
            if "=" in tok:
                k, v = tok.split("=", 1)
                pairs.append((k, v))
    except Exception:
        pass
    for k, v in pairs:
        if _ENV_OK.match(k) and v:
            os.environ[k] = v
            loaded += 1
    return loaded


def setup_isolation(run_dir: Path, snapshot: Path) -> None:
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True)
    shutil.copytree(snapshot / "data", run_dir / "data")
    (run_dir / "tmp").mkdir()
    os.environ["TMPDIR"] = str(run_dir / "tmp")
    import tempfile
    tempfile.tempdir = str(run_dir / "tmp")

    sys.path.insert(0, str(TESTS))
    import _live_data_guard as g  # noqa: E402
    extra_soft = [LIVE_CHECKOUT / "backend" / "data", LIVE_CHECKOUT / "max" / "memory.md",
                  HOME / "empire-repo-main" / "backend" / "data"]
    soft = set(g.SOFT_ROOTS) | set(g._forms(extra_soft))
    if g.REPO_ROOT.resolve() != LIVE_CHECKOUT.resolve():
        # this checkout is a worktree, not the live tree: its own backend/data is scratch
        soft -= set(g._forms([g.REPO_ROOT / "backend" / "data"]))
    g.SOFT_ROOTS = tuple(sorted(soft))
    g.redirect_env(run_dir)
    db = str(run_dir / "data" / "empire.db")
    for k in ("EMPIRE_TASK_DB", "EMPIRE_DB_PATH", "EMPIRE_DB"):
        os.environ[k] = db
    os.environ["EMPIRE_PHOTOS_DIR"] = str(run_dir / "data" / "photos")
    os.environ["EMPIRE_BRAIN_DIR"] = str(run_dir / "data" / "brain")
    os.environ["EMPIRE_REGRESSION_RUN"] = "1"
    g.write_sitecustomize(run_dir)
    g.install(str(run_dir / "live_data_violations.log"))

    def _send_firewall(event, args):
        if event == "socket.connect":
            addr = args[1] if len(args) > 1 else None
            if isinstance(addr, tuple) and len(addr) >= 2 and addr[1] in SMTP_PORTS:
                raise PermissionError(f"regression run: SMTP connect refused ({addr[1]})")
        elif event in ("socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyname_ex"):
            host = args[0] if args else ""
            if isinstance(host, bytes):
                host = host.decode("ascii", "ignore")
            if any(str(host or "").lower().rstrip(".") == h for h in BLOCKED_HOSTS):
                raise PermissionError(f"regression run: {host} refused (no outbound sends)")
    sys.addaudithook(_send_firewall)
    g.assert_isolated()


def install_recorders() -> None:
    sys.path.insert(0, str(BACKEND))
    os.chdir(BACKEND)
    from app.services.max import tool_executor as te
    from app.services.max.tool_executor import ToolResult
    import importlib
    R = importlib.import_module("app.routers.max.router")  # the module, not the APIRouter
    original = te.execute_tool

    def recorded_execute_tool(tool_call, *args, **kwargs):
        name = str((tool_call or {}).get("tool") or "?") if isinstance(tool_call, dict) else "?"
        _note(name)
        if name in DENY_TOOLS:
            return ToolResult(tool=name, success=False, error=f"{name} is disabled in this test copy")
        if name in SEND_TOOLS:
            raw = " ".join(str((tool_call or {}).get(k) or "") for k in ("to", "recipient", "recipient_email", "email", "cc"))
            addrs = {a.lower() for a in re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", raw)}
            ok = not addrs or addrs <= SELF_ADDRESSES
            SEND_LOG.append({"tool": name, "to": sorted(addrs) or ["(Rafael default)"], "allowed": ok})
            if not ok:
                return ToolResult(tool=name, success=False,
                                  error="recipient is not Rafael: needs Rafael's explicit yes before any send")
            atts = (tool_call or {}).get("attachments") or []
            n_att = len(atts) if isinstance(atts, list) else 1
            if name in ("send_quote_email", "send_invoice_email", "email_quote"):
                n_att = max(n_att, 1)
            # same proof fields the real tools return, so the truth check treats it like a real send
            return ToolResult(tool=name, success=True, result={
                "attachments_sent": n_att, "pdf_path": "/regression-test-copy/attachment.pdf" if n_att else None,
                "pdf_size_bytes": 24576 if n_att else 0,
                "sent": True, "verified": True, "to": sorted(addrs) or ["empirebox2026@gmail.com"],
                "subject": (tool_call or {}).get("subject") or "", "message_id": f"test-{int(time.time() * 1000)}",
                "quote_ids": (tool_call or {}).get("quote_ids") or (tool_call or {}).get("quote_id"),
                "path": (tool_call or {}).get("path") or (tool_call or {}).get("file"),
            })
        if name == "request_improvement":
            return ToolResult(tool=name, success=True, result={
                "id": 901, "status": "proposed", "title": (tool_call or {}).get("title") or "",
                "message": "Filed as improvement #901. Builds on a test copy after Rafael's approval tap."})
        return original(tool_call, *args, **kwargs)

    for mod in list(sys.modules.values()):
        try:
            if getattr(mod, "execute_tool", None) is original:
                setattr(mod, "execute_tool", recorded_execute_tool)
        except Exception:
            pass

    from app.services.max import quick_replies as qr
    _dr = qr.direct_reply

    def recorded_direct_reply(*a, **k):
        hit = _dr(*a, **k)
        if hit:
            _note(f"shortcut:{hit.get('skill')}")
        return hit
    qr.direct_reply = recorded_direct_reply

    from app.services.max import whatsapp_channel as wc
    _wdr = wc.whatsapp_doc_request

    async def recorded_doc_request(*a, **k):
        out = await _wdr(*a, **k)
        if out:
            _note("shortcut:wa_doc")
        return out
    wc.whatsapp_doc_request = recorded_doc_request
    try:
        from app.services.voice_documents import pipeline as vp
        _ing = vp.ingest_transcript

        def recorded_ingest(*a, **k):
            out = _ing(*a, **k)
            if isinstance(out, dict) and out.get("handled"):
                _note("shortcut:voice_draft")
            return out
        vp.ingest_transcript = recorded_ingest
    except Exception:
        pass

    _svc = R._chat_with_max_service

    async def recorded_service(*a, **k):
        resp = await _svc(*a, **k)
        mu = getattr(resp, "model_used", None) or (resp.get("model_used") if isinstance(resp, dict) else None)
        _note_model(mu)
        return resp
    R._chat_with_max_service = recorded_service


def _note_model(mu) -> None:
    mu = str(mu or "")
    if not mu:
        return
    if mu.startswith("quick-reply:"):
        _note("shortcut:" + mu.split(":", 1)[1])
    elif not LLM_HINT.search(mu):
        _note("shortcut:" + SHORTCUT_NAMES.get(mu, mu))
    else:
        _note("model")


async def run_studio(item: dict, label: str) -> dict:
    import importlib
    R = importlib.import_module("app.routers.max.router")
    from app.services.max import founder_session as fs
    tok = fs.set_current({"verified": True, "email": "rafa22giraldo@gmail.com", "via": "regression-test", "why": ""})
    texts, model_used, error = [], None, None
    try:
        req = R.ChatRequest(message=item["message"], channel="dashboard",
                            conversation_id=f"reg-{label}-{item['id']}", history=item.get("history") or [])
        resp = await R._chat_stream_impl(req)
        async for chunk in resp.body_iterator:
            s = chunk.decode() if isinstance(chunk, (bytes, bytearray)) else str(chunk)
            for line in s.splitlines():
                if not line.startswith("data: "):
                    continue
                try:
                    ev = json.loads(line[6:])
                except Exception:
                    continue
                if ev.get("type") == "text":
                    texts.append(str(ev.get("content") or ""))
                elif ev.get("type") == "gpu_safety_replace":
                    texts = [str(ev.get("replacement") or "")]
                elif ev.get("type") == "done":
                    model_used = ev.get("model_used")
                elif ev.get("type") == "error":
                    error = str(ev.get("content") or "stream error")[:300]
    finally:
        fs.reset_current(tok)
    _note_model(model_used)
    return {"text": "\n".join(t for t in texts if t).strip(), "model_used": model_used, "error": error}


async def run_whatsapp(item: dict, label: str, idx: int) -> dict:
    from app.services.max import whatsapp_channel as wc
    wa_id = f"1555010{idx:04d}"
    reply = await wc.default_text_handler(item["message"], wa_id)
    text, docs = wc._split_reply(reply)
    out = {"text": str(text or "").strip(), "documents": len(docs or [])}
    if docs:
        _note("wa:documents")
    return out


async def run_one(item: dict, label: str, idx: int, sem: asyncio.Semaphore, timeout: float) -> dict:
    async with sem:
        rec: list = []
        token = REC.set(rec)
        started = time.monotonic()
        try:
            for attempt in range(2):  # one retry on a transient provider/network failure
                if item["channel"] == "whatsapp":
                    out = await asyncio.wait_for(run_whatsapp(item, label, idx), timeout)
                else:
                    out = await asyncio.wait_for(run_studio(item, label), timeout)
                if not (out.get("error") or _PROVIDER_FAIL.search(out.get("text") or "")):
                    break
                rec.append("retry")
        except asyncio.TimeoutError:
            out = {"text": "", "error": f"timeout after {timeout:.0f}s"}
        except Exception as exc:  # pragma: no cover
            out = {"text": "", "error": f"{type(exc).__name__}: {exc}"[:300]}
        finally:
            REC.reset(token)
        out["tools"] = rec
        out["seconds"] = round(time.monotonic() - started, 1)
        print(f"[{label}] {item['id']} {out['seconds']}s tools={rec} words={len(out['text'].split())}", flush=True)
        return out


def known_quote_numbers(db_path: Path) -> set[str]:
    try:
        c = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        rows = c.execute("SELECT quote_number FROM quotes_v2 WHERE quote_number IS NOT NULL").fetchall()
        c.close()
        return {str(r[0]).upper() for r in rows}
    except Exception:
        return set()


async def main_async(args) -> int:
    from tests.max_regression.scoring import score_answer, summarize  # type: ignore
    data = json.loads((HERE / "questions.json").read_text())
    items = data["questions"]
    if args.ids:
        wanted = set(args.ids.split(","))
        items = [i for i in items if i["id"] in wanted]
    sem = asyncio.Semaphore(args.concurrency)
    results = await asyncio.gather(*(run_one(it, args.label, n, sem, args.timeout) for n, it in enumerate(items)))
    known = known_quote_numbers(Path(args.run_dir) / "data" / "empire.db")
    scores, records = {}, {}
    for it, rec in zip(items, results):
        records[it["id"]] = rec
        scores[it["id"]] = score_answer(it, rec, known_quotes=known or None)
    summary = summarize(scores)
    out = {"label": args.label, "git_head": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=BACKEND,
                                                            capture_output=True, text=True).stdout.strip(),
           "summary": summary, "scores": scores, "records": records, "sends": SEND_LOG,
           "questions": {i["id"]: {"kind": i["kind"], "channel": i["channel"], "message": i["message"]} for i in items}}
    Path(args.out).write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str))
    print("SUMMARY", json.dumps(summary))
    for qid, s in scores.items():
        if not s["pass"]:
            print(f"  FAIL {qid}: {'; '.join(s['notes'])[:300]}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", default="")
    ap.add_argument("--ids", default="")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--timeout", type=float, default=240)
    args = ap.parse_args()
    run_dir = Path(args.run_dir).resolve()
    if any(str(run_dir).startswith(str(p)) for p in (HOME / "empire-data", Path("/data/amp"), Path("/data/maxine"))):
        raise SystemExit("run-dir must not be inside live or family data")
    args.out = args.out or str(run_dir / "results.json")
    n = load_model_env()
    setup_isolation(run_dir, Path(args.snapshot).resolve())
    install_recorders()
    print(f"isolated run in {run_dir} ({n} model/search settings loaded)", flush=True)
    rc = asyncio.run(main_async(args))
    viol = run_dir / "live_data_violations.log"
    print("live-data refusals logged:", (len(viol.read_text().splitlines()) if viol.exists() else 0))
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(rc)  # background tasks of the Max stack must not keep the run alive


if __name__ == "__main__":
    main()
