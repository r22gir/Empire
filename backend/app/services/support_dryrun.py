"""Safe Empire support dry-run for nightly yes/no checks.

Exercises Luna (SupportDesk), isolated TEST ticket create, Pedir ayuda a
Max, desk routing, and the notification that WOULD go to Rafael.

Never sends email, WhatsApp, SMS, or Telegram. Never reads live contacts.
Writes only under a temp store and always deletes it.
Portable across Rafael's Max (workroom/studio) and Max-e / Maxine.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import sqlite3
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

TEST_MARK = "[TEST] EMPIRE SUPPORT DRY-RUN"
TEST_TICKET_PREFIX = "fh-dryrun-"
TEST_SENDER = "TEST requester (not a real contact)"
OWNER_NAME = "Rafael"
OWNER_ROLE = "owner"
FOUNDER_INBOX_LABEL = "founder-inbox (not disclosed)"
PLACEHOLDER_CONTACT = "owner-placeholder (not a real contact)"
FORBIDDEN_LIVE_PREFIXES = (
    "/data/amp",
    "/data/maxine",
    "/data/family-help",
    "/data/empire",
    "/home/rg/empire-data",
    "/home/rg/empire-repo/backend/data",
)

_ENV_KEYS = (
    "EMPIRE_EDITION",
    "EMPIRE_DATA_DIR",
    "FAMILY_HELP_INBOX_DIR",
    "FAMILY_HELP_FOUNDER_INBOX",
    "FAMILY_HELP_DB",
    "FAMILY_HELP_PEER_DIRS",
    "FAMILY_HELP_OWNER_ALERTS",
    "FAMILY_HELP_OWNER_PHONE",
    "FAMILY_HELP_OWNER_CHANNEL",
    "FAMILY_HELP_NOTIFY_EMAIL",
    "OWNER_PHONE",
    "RAFAEL_PHONE",
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_WHATSAPP_FROM",
    "WHATSAPP_ACCESS_TOKEN",
    "FAMILY_HELP_WHATSAPP_TOKEN",
    "FAMILY_HELP_SMS_TOKEN",
    "ASSISTANT_NAME",
    "INSTANCE_USAGE_CAP_PCT",
    "EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS",
    "SPRINT_M_DB",
    "EMPIRE_TEST_GUARD",
)

# Live phone / mail must never appear in dry-run output.
_CONTACT_ENV = (
    "FAMILY_HELP_OWNER_PHONE",
    "OWNER_PHONE",
    "RAFAEL_PHONE",
    "FAMILY_HELP_NOTIFY_EMAIL",
    "TWILIO_WHATSAPP_FROM",
)


@dataclass
class StepResult:
    name: str
    ok: bool
    detail: str
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> str:
        return "PASS" if self.ok else "FAIL"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ok": self.ok,
            "status": self.status,
            "detail": self.detail,
            "extra": self.extra,
        }


@dataclass
class DryRunReport:
    ok: bool
    support_working: bool
    edition: str
    assistant: str
    portable_to: list[str]
    steps: list[StepResult]
    ticket_id: Optional[str] = None
    notification: Optional[dict[str, Any]] = None
    sent: bool = False
    cleaned: bool = False
    isolated_root: Optional[str] = None

    @property
    def yes_no(self) -> str:
        return "yes" if self.support_working else "no"

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "support_working": self.support_working,
            "yes_no": self.yes_no,
            "dry_run": True,
            "sent": self.sent,
            "cleaned": self.cleaned,
            "edition": self.edition,
            "assistant": self.assistant,
            "portable_to": list(self.portable_to),
            "ticket_id": self.ticket_id,
            "notification": self.notification,
            "steps": [s.to_dict() for s in self.steps],
            "isolated_root_removed": self.cleaned,
        }


def current_edition() -> str:
    try:
        from app.edition import edition_name

        return edition_name()
    except Exception:
        raw = (os.getenv("EMPIRE_EDITION") or "").strip().lower()
        return raw or "workroom"


def current_assistant(edition: Optional[str] = None) -> str:
    try:
        from app.edition import assistant_name, edition_profile

        if edition in {None, "", current_edition()}:
            return assistant_name()
        profile = edition_profile() if not edition else None
        if profile:
            return str(profile.get("assistant_default") or "Max")
    except Exception:
        pass
    return {
        "amp": "Max-e",
        "maxine": "Maxine",
        "workroom": "Max",
        "studio": "Max",
    }.get((edition or current_edition()), "Max")


def test_ticket_message(edition: str) -> str:
    return (
        f"{TEST_MARK} Pedir ayuda a Max — isolated dry-run on {edition}. "
        "Do not notify clients. Discard after cleanup."
    )


def format_steps_text(report: DryRunReport) -> str:
    lines = [
        "Empire support dry-run",
        f"edition: {report.edition} ({report.assistant})",
        f"portable_to: {', '.join(report.portable_to)}",
        f"dry_run: true  sent: {str(report.sent).lower()}  cleaned: {str(report.cleaned).lower()}",
    ]
    for step in report.steps:
        lines.append(f"[{step.status}] {step.name}: {step.detail}")
    lines.append(f"SUPPORT WORKING: {report.yes_no.upper()}")
    return "\n".join(lines)


def _iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _assert_isolated(path: Path, root: Path) -> None:
    text = str(path.resolve())
    root_text = str(root.resolve())
    if not text.startswith(root_text):
        raise RuntimeError(f"refusing path outside isolated root: {path}")
    for prefix in FORBIDDEN_LIVE_PREFIXES:
        if text.startswith(prefix):
            raise RuntimeError(f"refusing live support path: {path}")


@contextmanager
def isolated_support_env(root: Path) -> Iterator[dict[str, Path]]:
    """Point family-help + sprint-m stores at ``root``. No live phones."""
    saved = {key: os.environ.get(key) for key in _ENV_KEYS}
    inbox = root / "family-help"
    help_db = root / "family-help-sprint" / "help.db"
    sprint_db = root / "sprint_m.db"
    # Do not name this "data": shutil.rmtree uses os.rmdir("data") with a
    # dir_fd, and the test live-data guard then abspaths that to backend/data.
    data_dir = root / "instance"
    inbox.mkdir(parents=True, exist_ok=True)
    help_db.parent.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.environ["FAMILY_HELP_INBOX_DIR"] = str(inbox)
        os.environ["FAMILY_HELP_FOUNDER_INBOX"] = str(inbox)
        os.environ["FAMILY_HELP_DB"] = str(help_db)
        os.environ["SPRINT_M_DB"] = str(sprint_db)
        os.environ["EMPIRE_DATA_DIR"] = str(data_dir)
        os.environ["EMPIRE_TEST_GUARD"] = "1"
        os.environ["FAMILY_HELP_OWNER_ALERTS"] = "false"
        os.environ["EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS"] = "1000000"
        os.environ["INSTANCE_USAGE_CAP_PCT"] = "20"
        for key in (
            "FAMILY_HELP_OWNER_PHONE",
            "OWNER_PHONE",
            "RAFAEL_PHONE",
            "FAMILY_HELP_NOTIFY_EMAIL",
            "TWILIO_ACCOUNT_SID",
            "TWILIO_AUTH_TOKEN",
            "TWILIO_WHATSAPP_FROM",
            "WHATSAPP_ACCESS_TOKEN",
            "FAMILY_HELP_WHATSAPP_TOKEN",
            "FAMILY_HELP_SMS_TOKEN",
            "FAMILY_HELP_PEER_DIRS",
        ):
            os.environ.pop(key, None)
        yield {
            "root": root,
            "inbox": inbox,
            "help_db": help_db,
            "sprint_db": sprint_db,
            "data_dir": data_dir,
        }
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _write_isolated_ticket(
    *,
    inbox: Path,
    edition: str,
    ticket_id: str,
    sender: str,
    message: str,
    root: Path,
) -> Path:
    folder = inbox / edition
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "help.db"
    _assert_isolated(path, root)
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS tickets (
                id TEXT PRIMARY KEY,
                edition TEXT NOT NULL,
                sender TEXT NOT NULL,
                message TEXT NOT NULL,
                transcript TEXT,
                context_json TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'new',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )"""
        )
        now = _iso()
        conn.execute(
            """INSERT INTO tickets
               (id, edition, sender, message, transcript, context_json, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, '', '[]', 'new', ?, ?)""",
            (ticket_id, edition, sender, message, now, now),
        )
        conn.commit()
    finally:
        conn.close()
    return path


def _ticket_exists(inbox: Path, edition: str, ticket_id: str) -> bool:
    path = inbox / edition / "help.db"
    if not path.is_file():
        return False
    conn = sqlite3.connect(str(path))
    try:
        row = conn.execute(
            "SELECT id FROM tickets WHERE id = ? AND edition = ?",
            (ticket_id, edition),
        ).fetchone()
        return bool(row)
    finally:
        conn.close()


def _run_async(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result(timeout=30)


def render_rafael_notification(ticket: dict[str, Any]) -> dict[str, Any]:
    """Render the founder notice that WOULD be sent. Never transmits."""
    edition = (ticket.get("edition") or "").strip().lower()
    label = "Max-e" if edition == "amp" else ("Maxine" if edition == "maxine" else "Max")
    title = f"{TEST_MARK} Ayuda de {label}: {ticket.get('sender') or TEST_SENDER}"
    preview = (ticket.get("message") or ticket.get("transcript") or "").strip()[:400]
    body = (
        f"{label} · ticket {ticket.get('id')}\n"
        f"{preview or '(audio o archivo sin texto)'}\n"
        "Abre el chat de Max → Ayuda de ediciones familiares.\n"
        "DRY-RUN: not sent."
    )
    html_body = (
        f"<p><strong>{title}</strong></p>"
        f"<p>Ticket <code>{ticket.get('id') or ''}</code></p>"
        f"<p>{preview or 'Audio o archivo adjunto.'}</p>"
        "<p>DRY-RUN — would reply from personal Max. No Telegram. Not sent.</p>"
    )
    whatsapp = (
        f"{TEST_MARK} NOT SENT\n"
        f"{OWNER_NAME} ({OWNER_ROLE}) would be notified:\n"
        f"{title}\n{preview}"
    )
    payload = {
        "dry_run": True,
        "sent": False,
        "channels": {
            "in_app": {
                "would_send": True,
                "source": "MAX",
                "type": "decision_needed",
                "title": title,
                "body": body,
                "priority": "high",
            },
            "email": {
                "would_send": True,
                "to_role": OWNER_ROLE,
                "to_name": OWNER_NAME,
                "to": FOUNDER_INBOX_LABEL,
                "subject": title,
                "html": html_body,
            },
            "whatsapp": {
                "would_send": False,
                "reason": "dry_run_never_sends",
                "to_role": OWNER_ROLE,
                "to_name": OWNER_NAME,
                "to": PLACEHOLDER_CONTACT,
                "preview": whatsapp,
            },
        },
        "recipient_name": OWNER_NAME,
        "recipient_role": OWNER_ROLE,
        "real_contacts_used": False,
        "owner_only": True,
        "sent_to_family": False,
        "max_sends_to_clients": False,
    }
    leaked = _contact_leaks(payload)
    if leaked:
        raise RuntimeError(f"dry-run notification leaked contacts: {leaked}")
    return payload


def _contact_leaks(payload: Any) -> list[str]:
    blob = str(payload)
    leaks: list[str] = []
    for key in _CONTACT_ENV:
        value = (os.getenv(key) or "").strip()
        if value and len(value) >= 6 and value in blob:
            leaks.append(key)
    for needle in ("empirebox2026@gmail.com", "whatsapp:+"):
        if needle in blob:
            leaks.append(needle)
    return leaks


def _step_desk_ready() -> StepResult:
    from app.services.max.desks.support_desk import SupportDesk

    desk = SupportDesk()
    ok = (
        desk.desk_id == "support"
        and desk.agent_name == "Luna"
        and "ticket_management" in desk.capabilities
    )
    return StepResult(
        name="desk_ready",
        ok=ok,
        detail="Luna SupportDesk loaded" if ok else "Luna SupportDesk missing or miswired",
        extra={
            "desk_id": desk.desk_id,
            "agent_name": desk.agent_name,
            "desk_name": desk.desk_name,
            "capabilities": list(desk.capabilities),
        },
    )


def _step_ticket_create(paths: dict[str, Path], edition: str) -> tuple[dict[str, Any], StepResult]:
    ticket_id = f"{TEST_TICKET_PREFIX}{uuid.uuid4().hex[:10]}"
    message = test_ticket_message(edition)
    store_edition = edition if edition in {"amp", "maxine"} else "amp"
    path = _write_isolated_ticket(
        inbox=paths["inbox"],
        edition=store_edition,
        ticket_id=ticket_id,
        sender=TEST_SENDER,
        message=message,
        root=paths["root"],
    )
    exists = _ticket_exists(paths["inbox"], store_edition, ticket_id)
    ticket = {
        "id": ticket_id,
        "edition": store_edition,
        "sender": TEST_SENDER,
        "message": message,
        "status": "new",
        "test": True,
        "isolated": True,
        "store": str(path),
    }
    ok = exists and TEST_MARK in message and ticket_id.startswith(TEST_TICKET_PREFIX)
    return ticket, StepResult(
        name="ticket_create",
        ok=ok,
        detail=f"{ticket_id} written to isolated {store_edition} store" if ok else "isolated TEST ticket missing",
        extra={"ticket_id": ticket_id, "store": str(path), "edition": store_edition},
    )


def _step_family_create(paths: dict[str, Path]) -> StepResult:
    """Prove Pedir ayuda ticket create on Max-e and Maxine without notify."""
    from app.edition import apply_amp_process_paths
    from app.services.family_help import create_ticket

    created: list[str] = []
    saved_edition = os.environ.get("EMPIRE_EDITION")
    saved_assistant = os.environ.get("ASSISTANT_NAME")
    saved_data = os.environ.get("EMPIRE_DATA_DIR")
    try:
        for edition, sender in (("amp", "Juan Diego Giraldo"), ("maxine", "Camilo Giraldo")):
            data = paths["root"] / edition
            data.mkdir(parents=True, exist_ok=True)
            os.environ["EMPIRE_EDITION"] = edition
            os.environ["EMPIRE_DATA_DIR"] = str(data)
            os.environ["ASSISTANT_NAME"] = "Max-e" if edition == "amp" else "Maxine"
            apply_amp_process_paths()
            ticket = create_ticket(
                message=test_ticket_message(edition),
                sender=sender,
                notify=False,
            )
            if not str(ticket.get("id") or "").startswith("fh-"):
                raise RuntimeError(f"{edition} ticket id unexpected: {ticket.get('id')}")
            if TEST_MARK not in (ticket.get("message") or ""):
                raise RuntimeError(f"{edition} ticket not marked TEST")
            created.append(f"{edition}:{ticket['id']}")
    finally:
        if saved_edition is None:
            os.environ.pop("EMPIRE_EDITION", None)
        else:
            os.environ["EMPIRE_EDITION"] = saved_edition
        if saved_assistant is None:
            os.environ.pop("ASSISTANT_NAME", None)
        else:
            os.environ["ASSISTANT_NAME"] = saved_assistant
        if saved_data is None:
            os.environ.pop("EMPIRE_DATA_DIR", None)
        else:
            os.environ["EMPIRE_DATA_DIR"] = saved_data
    return StepResult(
        name="family_create",
        ok=len(created) == 2,
        detail=f"Max-e + Maxine TEST tickets (notify=False): {', '.join(created)}",
        extra={"created": created},
    )


def _step_pedir_ayuda(paths: dict[str, Path]) -> StepResult:
    from app.services.family_help import is_help_intent, leftover_after_intent
    from app.services.sprint_m import family_alerts

    cue = "Pedir ayuda a Max — hem is uneven, need a fix"
    if not is_help_intent(cue):
        return StepResult(name="pedir_ayuda", ok=False, detail="help intent not recognized")
    leftover = leftover_after_intent(cue)
    alert = family_alerts.submit_family_request(
        requester="juan",
        message=f"{TEST_MARK} {leftover or cue}",
        source="Pedir ayuda a Max",
        request_id=f"dryrun-{uuid.uuid4().hex[:8]}",
    )
    if alert.get("sent_to_family") or alert.get("delivery_status") not in {"noop", "queued_not_sent"}:
        return StepResult(
            name="pedir_ayuda",
            ok=False,
            detail=f"unexpected delivery {alert.get('delivery_status')}",
            extra={"alert": {k: alert.get(k) for k in ("delivery_status", "noop_reason", "recipient_role")}},
        )
    if alert.get("recipient_name") != OWNER_NAME or alert.get("recipient_role") != OWNER_ROLE:
        return StepResult(name="pedir_ayuda", ok=False, detail="owner routing is not Rafael")
    if alert.get("recipient"):
        return StepResult(name="pedir_ayuda", ok=False, detail="real recipient leaked into alert")
    help_db = paths["help_db"]
    _assert_isolated(help_db, paths["root"])
    if not help_db.is_file():
        return StepResult(name="pedir_ayuda", ok=False, detail="isolated family-help db missing")
    return StepResult(
        name="pedir_ayuda",
        ok=True,
        detail=(
            f"intent matched; owner alert {alert.get('delivery_status')} "
            f"(not sent) for {OWNER_NAME}"
        ),
        extra={
            "classification": alert.get("classification"),
            "delivery_status": alert.get("delivery_status"),
            "requester_agent": alert.get("requester_agent"),
            "owner_only": alert.get("owner_only"),
        },
    )


def _step_desk_route(ticket: dict[str, Any]) -> StepResult:
    from app.services.max.desks.base_desk import DeskTask, TaskPriority, TaskState
    from app.services.max.desks.support_desk import SupportDesk

    desk = SupportDesk()
    telegram_calls: list[str] = []

    async def _no_telegram(message: str) -> bool:
        telegram_calls.append(message)
        return False

    async def _no_ai(prompt: str, model_preference: Optional[str] = None) -> str:
        return ""

    desk.notify_telegram = _no_telegram  # type: ignore[method-assign]
    desk.ai_call = _no_ai  # type: ignore[method-assign]
    desk._log_to_brain = lambda *args, **kwargs: None  # type: ignore[method-assign]
    desk._telegram = None
    desk._memory_store = False

    task = DeskTask(
        id=f"dryrun-task-{uuid.uuid4().hex[:8]}",
        title=f"{TEST_MARK} ticket help desk",
        description=ticket.get("message") or test_ticket_message("workroom"),
        priority=TaskPriority.NORMAL,
        source="support_dryrun",
        customer_name=TEST_SENDER,
    )
    result = _run_async(desk.handle_task(task))
    actions = [a.action for a in (result.actions or [])]
    ok = (
        result.state in {TaskState.COMPLETED, TaskState.ESCALATED}
        and ("ticket_triage" in actions or "accepted" in actions)
        and not telegram_calls
    )
    return StepResult(
        name="desk_route",
        ok=ok,
        detail=(
            f"Luna {result.state.value}; actions={actions}"
            if ok
            else f"Luna did not complete ticket (state={result.state.value}, actions={actions})"
        ),
        extra={
            "state": result.state.value,
            "actions": actions,
            "telegram_calls": len(telegram_calls),
            "result_preview": (result.result or "")[:240],
        },
    )


def _step_notify_render(ticket: dict[str, Any]) -> tuple[dict[str, Any], StepResult]:
    payload = render_rafael_notification(ticket)
    channels = payload.get("channels") or {}
    email = channels.get("email") or {}
    in_app = channels.get("in_app") or {}
    ok = (
        payload.get("sent") is False
        and payload.get("dry_run") is True
        and payload.get("real_contacts_used") is False
        and email.get("to") == FOUNDER_INBOX_LABEL
        and email.get("to_name") == OWNER_NAME
        and TEST_MARK in (in_app.get("title") or "")
        and not payload.get("sent_to_family")
    )
    return payload, StepResult(
        name="notify_render",
        ok=ok,
        detail=(
            f"email+in-app drafted for {OWNER_NAME}; sent=false"
            if ok
            else "notification render failed safety checks"
        ),
        extra={
            "channels": sorted(channels),
            "to_role": email.get("to_role"),
            "to_name": email.get("to_name"),
        },
    )


def _step_cleanup(root: Path) -> StepResult:
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    leftover = root.exists()
    if leftover:
        # Last resort: unlink files then directories (absolute paths).
        try:
            for dirpath, dirnames, filenames in os.walk(root, topdown=False):
                for name in filenames:
                    Path(dirpath, name).unlink(missing_ok=True)
                for name in dirnames:
                    child = Path(dirpath, name)
                    try:
                        child.rmdir()
                    except OSError:
                        pass
            root.rmdir()
        except OSError:
            pass
        leftover = root.exists()
    ok = not leftover
    return StepResult(
        name="cleanup",
        ok=ok,
        detail="isolated store removed" if ok else f"cleanup leftover at {root}",
        extra={"root": str(root), "removed": not leftover},
    )


def run_support_dryrun(*, edition: Optional[str] = None) -> DryRunReport:
    """Run the isolated support dry-run and return a structured report."""
    live_edition = edition or current_edition()
    assistant = current_assistant(live_edition)
    steps: list[StepResult] = []
    ticket: dict[str, Any] | None = None
    notification: dict[str, Any] | None = None
    root = Path(tempfile.mkdtemp(prefix="empire-support-dryrun-"))
    cleaned = False
    try:
        with isolated_support_env(root) as paths:
            steps.append(_step_desk_ready())
            try:
                ticket, create_step = _step_ticket_create(paths, live_edition)
                steps.append(create_step)
            except Exception as exc:
                steps.append(StepResult("ticket_create", False, f"{type(exc).__name__}: {exc}"))
            try:
                steps.append(_step_family_create(paths))
            except Exception as exc:
                steps.append(StepResult("family_create", False, f"{type(exc).__name__}: {exc}"))
            try:
                steps.append(_step_pedir_ayuda(paths))
            except Exception as exc:
                steps.append(StepResult("pedir_ayuda", False, f"{type(exc).__name__}: {exc}"))
            try:
                if ticket:
                    steps.append(_step_desk_route(ticket))
                else:
                    steps.append(StepResult("desk_route", False, "skipped; no TEST ticket"))
            except Exception as exc:
                steps.append(StepResult("desk_route", False, f"{type(exc).__name__}: {exc}"))
            try:
                if ticket:
                    notification, notify_step = _step_notify_render(ticket)
                    steps.append(notify_step)
                else:
                    steps.append(StepResult("notify_render", False, "skipped; no TEST ticket"))
            except Exception as exc:
                steps.append(StepResult("notify_render", False, f"{type(exc).__name__}: {exc}"))
    except Exception as exc:
        steps.append(StepResult("isolated_env", False, f"{type(exc).__name__}: {exc}"))
    finally:
        cleanup = _step_cleanup(root)
        steps.append(cleanup)
        cleaned = cleanup.ok

    required = {
        "desk_ready",
        "ticket_create",
        "family_create",
        "pedir_ayuda",
        "desk_route",
        "notify_render",
        "cleanup",
    }
    present = {s.name for s in steps}
    ok = all(s.ok for s in steps if s.name in required) and required <= present
    return DryRunReport(
        ok=ok,
        support_working=ok,
        edition=live_edition,
        assistant=assistant,
        portable_to=["workroom", "amp", "maxine"],
        steps=steps,
        ticket_id=(ticket or {}).get("id"),
        notification=notification,
        sent=False,
        cleaned=cleaned,
        isolated_root=str(root),
    )


def report_as_dict(report: DryRunReport) -> dict[str, Any]:
    return report.to_dict()
