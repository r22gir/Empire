"""HOTFIX 4.1 (2026-07-16) — Confirm Selection PIN bypass regression tests.

Production defect (per directive):
  On QuoteReviewScreen, "Confirm Selection" fired a customer-side
  ACCEPT ("Quote accepted!" toast) with NO PIN prompt, on a quote in
  founder_review (id=52, EST-2026-111, ~5:21 PM today). Founder approval
  is a Level-0 op. The bypass let a front-end-only mutation move
  draft/founder_review -> accepted (customer-side terminal status)
  without any PIN gate.

ROOT CAUSE (two layers):
  1. Frontend QuoteReviewScreen action 'confirm' PATCHed
     /quotes-v2/{id} with body {status: 'accepted', ...}. The
     server-side PATCH had 'status' in its updatable whitelist,
     so the PATCH succeeded.
  2. The dedicated /approve route (with _require_founder_pin) was
     bypassed via the PATCH path entirely.

FIX:
  Frontend:
    - "Confirm Selection" renamed "Save Tier"; PATCH only the
      selected_proposal + selected_tier (NO status change).
    - New "Approve & Send" button (draft/founder_review only) opens
      a PIN modal that calls POST /quotes-v2/{id}/approve with
      founder_pin in the body.

  Backend (defense in depth):
    - 'status' REMOVED from update_quote's updatable whitelist.
      PATCH can no longer mutate status. Status transitions route
      through /submit-for-review, /approve, /reject.

  Audit:
    - Quote 52 (EST-2026-111) corrected: status='accepted' reverted
      to 'founder_review' with 2 new financial_audit_log rows
      (corrective_reversal + hotfix_4_1_marker). Recorded in the
      module-level docstring of test_quote_52_audit_trail_recorded.
"""
from __future__ import annotations

import importlib
import os
import sqlite3
import sys
from pathlib import Path

import pytest


_BACKEND = Path(__file__).resolve().parents[1]


# ───────────────────────────────────────────────────────────────────
# Module-scope fixtures
# ───────────────────────────────────────────────────────────────────


@pytest.fixture
def founder_pin_active(monkeypatch):
    """Activate a known PIN. Hot-reload access_control + rebind the
    symbols in quote_service so the module-scoped FOUNDER_APPROVAL_PIN
    sees "7777" for the duration of this test.

    FOUNDER_APPROVAL_PIN is captured at import time in
    access_control.py; setenv alone is not enough. We reload the
    module and rebind the imported symbols in quote_service.
    """
    monkeypatch.setenv("FOUNDER_APPROVAL_PIN", "7777")
    if "app.services.max.access_control" in sys.modules:
        importlib.reload(sys.modules["app.services.max.access_control"])
    import app.services.max.access_control as ac_fresh
    import app.services.quote_service as qs
    monkeypatch.setattr(
        qs, "FOUNDER_APPROVAL_PIN", ac_fresh.FOUNDER_APPROVAL_PIN
    )
    monkeypatch.setattr(
        qs, "verify_founder_approval", ac_fresh.verify_founder_approval
    )
    return "7777"


def _create_quote(overrides=None):
    from app.services.quote_service import create_quote
    base = {
        "customer_name": "TrustTest",
        "business_unit": "workroom",
        "line_items": [
            {"category": "", "description": "x",
             "quantity": 1, "unit_price": 100.0},
        ],
        "tax_rate": 0.0,
        "project_name": "trust-test",
    }
    if overrides:
        base.update(overrides)
    return create_quote(base)["id"]


# ───────────────────────────────────────────────────────────────────
# (1) PATCH cannot mutate status (server-side defense)
# ───────────────────────────────────────────────────────────────────


class TestPatchWhitelistExcludesStatus:
    """PATCH must NOT accept 'status' in the body. Defends against
    the Confirm Selection bypass at the server edge."""

    def test_patch_attempting_status_accepted_is_silently_dropped(
            self, isolated_empire_db):
        """A buggy/prompt-injected frontend PATCHing status='accepted'
        must NOT change the status field."""
        from app.services.quote_service import (
            create_quote, submit_for_review, update_quote,
        )
        qid = _create_quote()
        submit_for_review(qid, changed_by="api")

        conn = sqlite3.connect(os.environ["EMPIRE_TASK_DB"])
        try:
            row = conn.execute(
                "SELECT status FROM quotes_v2 WHERE id = ?", (qid,)
            ).fetchone()
            assert row[0] == "founder_review"
        finally:
            conn.close()

        update_quote(qid, {"status": "accepted", "tax_rate": 0.10})

        conn = sqlite3.connect(os.environ["EMPIRE_TASK_DB"])
        try:
            row = conn.execute(
                "SELECT status, tax_rate FROM quotes_v2 WHERE id = ?",
                (qid,),
            ).fetchone()
            assert row[0] != "accepted", (
                f"HOTFIX FAILED — PATCH successfully set "
                f"status='accepted'; actual status={row[0]!r}"
            )
            assert row[0] == "founder_review", (
                f"status must STILL be founder_review after bypass "
                f"attempt; got {row[0]!r}"
            )
            assert row[1] == 0.10, (
                f"tax_rate SHOULD update (still whitelisted); "
                f"got {row[1]!r}"
            )
        finally:
            conn.close()

    def test_patch_attempting_status_to_any_value_dropped(
            self, isolated_empire_db):
        """Same guard for any status string."""
        from app.services.quote_service import update_quote
        qid = _create_quote()
        update_quote(qid, {"status": "founder_review"})
        conn = sqlite3.connect(os.environ["EMPIRE_TASK_DB"])
        try:
            row = conn.execute(
                "SELECT status FROM quotes_v2 WHERE id = ?", (qid,)
            ).fetchone()
            assert row[0] == "draft"
        finally:
            conn.close()

    def test_other_fields_still_patchable(self, isolated_empire_db):
        """Sanity: whitelist removal must NOT over-block."""
        from app.services.quote_service import update_quote
        qid = _create_quote()
        update_quote(qid, {
            "tax_rate": 0.0825, "deposit_percent": 60,
            "notes": "PO confirmed",
        })
        conn = sqlite3.connect(os.environ["EMPIRE_TASK_DB"])
        try:
            row = conn.execute(
                "SELECT tax_rate, deposit_percent, notes "
                "FROM quotes_v2 WHERE id = ?", (qid,),
            ).fetchone()
            assert abs(row[0] - 0.0825) < 1e-6
            assert row[1] == 60
            assert row[2] == "PO confirmed"
        finally:
            conn.close()


# ───────────────────────────────────────────────────────────────────
# (2) PIN-gated approve endpoint
# ───────────────────────────────────────────────────────────────────


class TestApproveEndpointRequiresPin:
    """POST /quotes-v2/{id}/approve is the ONLY legitimate path to
    draft/founder_review -> sent. Without a valid founder_pin it
    must reject."""

    def test_approve_with_wrong_pin_is_rejected(
            self, isolated_empire_db, founder_pin_active):
        """Wrong PIN must raise InvalidFounderPin."""
        from app.services.quote_service import (
            create_quote, submit_for_review, approve_quote,
            InvalidFounderPin,
        )
        qid = _create_quote()
        submit_for_review(qid, changed_by="api")
        with pytest.raises(InvalidFounderPin):
            approve_quote(
                qid, changed_by="founder", founder_pin="WRONG"
            )
        conn = sqlite3.connect(os.environ["EMPIRE_TASK_DB"])
        try:
            row = conn.execute(
                "SELECT status FROM quotes_v2 WHERE id = ?", (qid,)
            ).fetchone()
            assert row[0] == "founder_review"
        finally:
            conn.close()

    def test_approve_with_correct_pin_moves_to_sent(
            self, isolated_empire_db, founder_pin_active):
        """Right PIN: founder_review -> sent, sent_at populated, audit
        row written with reason."""
        from app.services.quote_service import (
            create_quote, submit_for_review, approve_quote,
        )
        qid = _create_quote()
        submit_for_review(qid, changed_by="api")
        result = approve_quote(
            qid, changed_by="founder",
            founder_pin=founder_pin_active,
            reason="PIN-gated approve via service (HOTFIX 4.1 test)",
        )
        assert result is not None
        conn = sqlite3.connect(os.environ["EMPIRE_TASK_DB"])
        try:
            row = conn.execute(
                "SELECT status, sent_at FROM quotes_v2 WHERE id = ?",
                (qid,),
            ).fetchone()
            assert row[0] == "sent"
            assert row[1] is not None, "sent_at must be populated"
            audit = conn.execute(
                "SELECT new_value, reason FROM financial_audit_log "
                "WHERE entity_type='quote' AND entity_id=? "
                "AND action='approve'",
                (qid,),
            ).fetchone()
            assert audit is not None, "approve audit row must exist"
            assert audit[0] == "sent"
            assert "PIN-gated approve" in (audit[1] or "")
        finally:
            conn.close()

    def test_approve_with_no_pin_is_rejected(
            self, isolated_empire_db, founder_pin_active):
        from app.services.quote_service import (
            create_quote, submit_for_review, approve_quote,
            InvalidFounderPin,
        )
        qid = _create_quote()
        submit_for_review(qid, changed_by="api")
        with pytest.raises(InvalidFounderPin):
            approve_quote(qid, changed_by="founder", founder_pin=None)
        conn = sqlite3.connect(os.environ["EMPIRE_TASK_DB"])
        try:
            row = conn.execute(
                "SELECT status FROM quotes_v2 WHERE id = ?", (qid,)
            ).fetchone()
            assert row[0] == "founder_review"
        finally:
            conn.close()

    def test_approve_with_empty_string_pin_is_rejected(
            self, isolated_empire_db, founder_pin_active):
        from app.services.quote_service import (
            create_quote, submit_for_review, approve_quote,
            InvalidFounderPin,
        )
        qid = _create_quote()
        submit_for_review(qid, changed_by="api")
        with pytest.raises(InvalidFounderPin):
            approve_quote(qid, changed_by="founder", founder_pin="")
        conn = sqlite3.connect(os.environ["EMPIRE_TASK_DB"])
        try:
            row = conn.execute(
                "SELECT status FROM quotes_v2 WHERE id = ?", (qid,)
            ).fetchone()
            assert row[0] == "founder_review"
        finally:
            conn.close()


# ───────────────────────────────────────────────────────────────────
# (3) Full reproduction: PATCH + approve round-trip
# ───────────────────────────────────────────────────────────────────


def test_full_bypass_attempt_via_patch_then_real_approve(
        isolated_empire_db, founder_pin_active):
    """The full reproduction at the service layer:
      1. PATCH status='accepted' must be silently dropped
      2. approve_quote with wrong PIN must raise
      3. approve_quote with right PIN succeeds and writes audit row

    This is the canonical path the new frontend button takes."""
    from app.services.quote_service import (
        update_quote, approve_quote, submit_for_review, InvalidFounderPin,
    )
    qid = _create_quote()
    submit_for_review(qid, changed_by="api")

    # 1. PATCH status='accepted' — silently dropped (whitelist guard).
    update_quote(qid, {"status": "accepted"})
    conn = sqlite3.connect(os.environ["EMPIRE_TASK_DB"])
    try:
        row = conn.execute(
            "SELECT status FROM quotes_v2 WHERE id = ?", (qid,)
        ).fetchone()
        assert row[0] == "founder_review"
    finally:
        conn.close()

    # 2. approve with wrong PIN — raises InvalidFounderPin.
    with pytest.raises(InvalidFounderPin):
        approve_quote(qid, changed_by="founder", founder_pin="WRONG")

    # 3. approve with correct PIN — succeeds.
    result = approve_quote(
        qid, changed_by="founder", founder_pin=founder_pin_active,
        reason="full-flow service-level test (HOTFIX 4.1)",
    )
    assert result is not None
    conn = sqlite3.connect(os.environ["EMPIRE_TASK_DB"])
    try:
        row = conn.execute(
            "SELECT status FROM quotes_v2 WHERE id = ?", (qid,)
        ).fetchone()
        assert row[0] == "sent"
    finally:
        conn.close()


# ───────────────────────────────────────────────────────────────────
# (4) Quote 52 audit trail (real prod-DB migration, recorded)
# ───────────────────────────────────────────────────────────────────


def test_quote_52_audit_trail_recorded_in_test_module_docstring():
    """The prod-side fix for quote 52 (EST-2026-111, The Channel -
    Bozzuto) was committed during HOTFIX 4.1 application:
    - status='accepted' reverted to 'founder_review'
    - 2 new financial_audit_log rows: corrective_reversal +
      hotfix_4_1_marker

    This test pins that contract by reading the prod DB directly.
    The migration was a one-shot SQL correction; future rebuilds
    must preserve these rows.
    """
    DB = os.path.expanduser("~/empire-data/empire.db")
    if not os.path.exists(DB):
        pytest.skip("prod DB not available in this test env")
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("""
            SELECT action, old_value, new_value, changed_by, reason
            FROM financial_audit_log
            WHERE entity_type='quote' AND entity_id='52'
              AND action IN ('corrective_reversal', 'hotfix_4_1_marker')
            ORDER BY id
        """).fetchall()
        actions = [r["action"] for r in rows]
        assert "corrective_reversal" in actions, (
            "corrective_reversal audit row missing for quote 52 — "
            "the prod-side migration was lost or never applied"
        )
        reversal = next(
            r for r in rows if r["action"] == "corrective_reversal"
        )
        assert reversal["old_value"] == "accepted"
        assert reversal["new_value"] == "founder_review"
        assert "HOTFIX 4.1" in (reversal["reason"] or "")
    finally:
        conn.close()
