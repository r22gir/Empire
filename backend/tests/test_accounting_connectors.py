"""Accounting connectors — QBO sandbox pull + Alegra/Siigo DIAN stub."""
import importlib

from fastapi import HTTPException

from app.services.accounting.guards import LiveWriteBlocked, SandboxOnlyError


def _load(monkeypatch, tmp_path, **env):
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))
    defaults = {
        "EMPIRE_EDITION": "studio",
        "FEATURE_QBO_SYNC": "false",
        "FEATURE_ALEGRA_SIIGO": "false",
        "QBO_ENVIRONMENT": "sandbox",
        "QBO_API_BASE": "https://sandbox-quickbooks.api.intuit.com",
        "ALEGRA_API_BASE": "https://api.sandbox.alegra.com",
        "SIIGO_API_BASE": "https://api-sandbox.siigo.com",
    }
    defaults.update(env)
    for key, val in defaults.items():
        monkeypatch.setenv(key, val)

    from app.db import database

    importlib.reload(database)

    from app.db import init_db

    importlib.reload(init_db)
    init_db.init_database()

    from app.routers import accounting_connectors
    from app.services import feature_flags
    from app.services.accounting import alegra_siigo, qbo

    importlib.reload(feature_flags)
    importlib.reload(qbo)
    importlib.reload(alegra_siigo)
    importlib.reload(accounting_connectors)
    return accounting_connectors, qbo, alegra_siigo, database


def test_qbo_disabled_without_flag(monkeypatch, tmp_path):
    routes, _qbo, _dian, _db = _load(monkeypatch, tmp_path, FEATURE_QBO_SYNC="false")
    try:
        routes.qbo_sync()
        assert False, "expected flag gate"
    except HTTPException as exc:
        assert exc.status_code == 403


def test_qbo_disabled_on_maxine_edition(monkeypatch, tmp_path):
    routes, _qbo, _dian, _db = _load(
        monkeypatch,
        tmp_path,
        EMPIRE_EDITION="maxine",
        FEATURE_QBO_SYNC="true",
    )
    try:
        routes.qbo_sync()
        assert False, "QBO is Studio/Empire only"
    except HTTPException as exc:
        assert exc.status_code == 403


def test_qbo_sandbox_pull_does_not_write_live_or_empire_invoices(monkeypatch, tmp_path):
    routes, qbo, _dian, database = _load(
        monkeypatch,
        tmp_path,
        EMPIRE_EDITION="studio",
        FEATURE_QBO_SYNC="true",
    )
    result = routes.qbo_sync()
    assert result["live_writes"] is False
    assert result["wrote_to_qbo"] is False
    assert result["wrote_to_empire_invoices"] is False
    assert result["invoices_pulled"] == 2
    assert result["payments_pulled"] == 2
    assert result["mode"] == "sandbox_pull"

    invoices = routes.qbo_invoices()["invoices"]
    payments = routes.qbo_payments()["payments"]
    assert {i["doc_number"] for i in invoices} == {"QBO-SAND-1001", "QBO-SAND-1002"}
    assert len(payments) == 2

    with database.get_db() as conn:
        empire_invoices = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
        empire_payments = conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
        assert empire_invoices == 0
        assert empire_payments == 0

    try:
        routes.qbo_push_invoice_blocked()
        assert False, "push must be blocked"
    except HTTPException as exc:
        assert exc.status_code == 403


def test_qbo_rejects_production_url(monkeypatch, tmp_path):
    _routes, qbo, _dian, _db = _load(
        monkeypatch,
        tmp_path,
        EMPIRE_EDITION="empire",
        FEATURE_QBO_SYNC="true",
        QBO_API_BASE="https://quickbooks.api.intuit.com",
    )
    try:
        qbo.qbo_sandbox_base()
        assert False, "production QBO host must be refused"
    except SandboxOnlyError as exc:
        assert exc.status_code == 403


def test_qbo_rejects_non_sandbox_environment(monkeypatch, tmp_path):
    _routes, qbo, _dian, _db = _load(
        monkeypatch,
        tmp_path,
        EMPIRE_EDITION="studio",
        FEATURE_QBO_SYNC="true",
        QBO_ENVIRONMENT="production",
    )
    try:
        qbo.qbo_sandbox_base()
        assert False, "production environment must be refused"
    except SandboxOnlyError as exc:
        assert exc.status_code == 403


def test_alegra_siigo_disabled_on_studio(monkeypatch, tmp_path):
    routes, _qbo, _dian, _db = _load(
        monkeypatch,
        tmp_path,
        EMPIRE_EDITION="studio",
        FEATURE_ALEGRA_SIIGO="true",
    )
    try:
        routes.dian_status()
        assert False, "DIAN stub is Maxine only"
    except HTTPException as exc:
        assert exc.status_code == 403


def test_alegra_siigo_stub_local_draft_and_blocks_dian_submit(monkeypatch, tmp_path):
    routes, _qbo, dian, _db = _load(
        monkeypatch,
        tmp_path,
        EMPIRE_EDITION="maxine",
        FEATURE_ALEGRA_SIIGO="true",
    )
    status = routes.dian_status()
    assert status["live_submit"] is False
    assert status["dian_submit_enabled"] is False
    assert status["mode"] == "sandbox_stub"

    created = routes.dian_local_draft(
        routes.DianDraftCreate(
            provider="siigo",
            customer_name="Cliente Sandbox",
            amount=190000,
            currency="COP",
        ),
    )
    assert created["live_submitted"] is False
    assert created["dian_cufe"] is None
    assert created["draft"]["status"] == "local_draft"

    drafts = routes.dian_drafts()["drafts"]
    assert len(drafts) == 1

    try:
        routes.dian_submit_blocked(draft_id=created["draft"]["id"])
        assert False, "DIAN submit must be blocked"
    except HTTPException as exc:
        assert exc.status_code == 403

    try:
        dian.push_to_provider(created["draft"]["id"], "alegra")
        assert False, "provider push must be blocked"
    except LiveWriteBlocked:
        pass


def test_accounting_status_never_claims_live_writes(monkeypatch, tmp_path):
    routes, _qbo, _dian, _db = _load(monkeypatch, tmp_path)
    body = routes.accounting_status()
    assert body["live_data_writes"] is False
    assert body["sandbox_credentials_only"] is True
    assert body["reads_client_aliases"] is False
    assert body["reads_business_json"] is False
    assert body["flags"]["auto_replies"] is False
