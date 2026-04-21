from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db import database
from app.main import app


client = TestClient(app)


def _use_temp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "vendorops.db"
    monkeypatch.setattr(database, "DB_PATH", str(db_path))
    return db_path


def test_vendorops_plans_and_status_are_standalone(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)

    plans = client.get("/api/v1/vendorops/plans")
    assert plans.status_code == 200
    body = plans.json()
    assert body["route_prefix"] == "/api/v1/vendorops"
    assert body["db_prefix"] == "vo_"
    assert body["standalone_add_on"] is True

    status = client.get("/api/v1/vendorops/status?tier=free")
    assert status.status_code == 200
    assert status.json()["max_can_query"] is True
    assert status.json()["max_can_write"] is False


def test_vendorops_free_tier_approval_limit(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)

    for idx in range(3):
        response = client.post(
            "/api/v1/vendorops/approvals",
            json={"tier": "free", "vendor_name": f"Vendor {idx}", "requested_action": "assisted signup"},
        )
        assert response.status_code == 200

    over_limit = client.post(
        "/api/v1/vendorops/approvals",
        json={"tier": "free", "vendor_name": "Vendor 4", "requested_action": "assisted signup"},
    )
    assert over_limit.status_code == 402
    assert "approval_limit" in over_limit.json()["detail"]


def test_vendorops_approval_round_trip_and_credential_audit(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)

    approval = client.post(
        "/api/v1/vendorops/approvals",
        json={"tier": "starter", "vendor_name": "Acme Vendor", "requested_action": "provision account"},
    ).json()["approval"]

    blocked = client.post(
        f"/api/v1/vendorops/approvals/{approval['id']}/approve",
        json={"explicit_founder_confirmation": False},
    )
    assert blocked.status_code == 403

    approved = client.post(
        f"/api/v1/vendorops/approvals/{approval['id']}/approve",
        json={"explicit_founder_confirmation": True},
    )
    assert approved.status_code == 200
    assert approved.json()["approval"]["status"] == "approved"

    raw_ref = "vault://vendorops/acme-founder-login"
    account_response = client.post(
        "/api/v1/vendorops/accounts",
        json={
            "tier": "starter",
            "approval_id": approval["id"],
            "vendor_name": "Acme Vendor",
            "credential_ref": raw_ref,
            "credential_owner": "founder",
            "explicit_founder_confirmation": True,
        },
    )
    assert account_response.status_code == 200
    account = account_response.json()["account"]
    assert account["credential_ref_masked"] != raw_ref
    assert "credential_ref_hash" in account
    assert raw_ref not in str(account)
    assert account["provisioning_trail"]["verification_boundary"] == "founder_approval_required_before_external_action"

    audit = client.get("/api/v1/vendorops/audit").json()["events"]
    assert any(event["event_type"] == "account_provisioning_trail_created" for event in audit)
    assert raw_ref not in str(audit)


def test_vendorops_rejects_plaintext_credentials(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)

    approval = client.post(
        "/api/v1/vendorops/approvals",
        json={"tier": "starter", "vendor_name": "Plaintext Vendor", "requested_action": "provision account"},
    ).json()["approval"]
    client.post(
        f"/api/v1/vendorops/approvals/{approval['id']}/approve",
        json={"explicit_founder_confirmation": True},
    )

    response = client.post(
        "/api/v1/vendorops/accounts",
        json={
            "tier": "starter",
            "approval_id": approval["id"],
            "vendor_name": "Plaintext Vendor",
            "credential_ref": "vault://vendorops/plaintext",
            "password": "never-store-this",
            "explicit_founder_confirmation": True,
        },
    )
    assert response.status_code == 400
    assert "plaintext credential" in str(response.json()).lower()


def test_vendorops_renewal_alerts_and_cancellation_monitoring(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    renewal_date = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()

    created = client.post(
        "/api/v1/vendorops/subscriptions",
        json={
            "tier": "starter",
            "vendor_name": "Renewal Vendor",
            "plan_name": "Starter",
            "renewal_date": renewal_date,
            "license_ref": "lic-renewal-secret",
            "explicit_founder_confirmation": True,
        },
    )
    assert created.status_code == 200
    subscription = created.json()["subscription"]
    assert subscription["license_ref_masked"] != "lic-renewal-secret"

    alerts = client.get("/api/v1/vendorops/renewal-alerts?days=14")
    assert alerts.status_code == 200
    assert any(item["id"] == subscription["id"] for item in alerts.json()["alerts"])

    canceled = client.post(
        f"/api/v1/vendorops/subscriptions/{subscription['id']}/cancel",
        json={"explicit_founder_confirmation": True},
    )
    assert canceled.status_code == 200
    assert canceled.json()["subscription"]["cancellation_state"] == "founder_confirmed_monitoring"


def test_vendorops_max_query_only_write_gate(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)

    summary = client.get("/api/v1/vendorops/max-summary?tier=pro")
    assert summary.status_code == 200
    assert summary.json()["vendorops"]["max_can_query"] is True

    write_attempt = client.post(
        "/api/v1/vendorops/max-action",
        json={"action": "approve", "target_type": "approval", "target_id": "voap_old"},
    )
    assert write_attempt.status_code == 403
    assert "query-only" in write_attempt.json()["detail"]
