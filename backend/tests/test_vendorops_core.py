from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db import database
from app.main import app
import app.routers.vendorops as vendorops_router


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
            "monthly_cost_usd": 12.5,
            "renewal_cadence": "monthly",
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
    alert_rows = alerts.json()["alerts"]
    assert any(item["subscription_id"] == subscription["id"] for item in alert_rows)
    alert = next(item for item in alert_rows if item["subscription_id"] == subscription["id"])
    assert alert["alert_type"] == "7_day"
    assert alert["delivery_status"] == "queued"
    assert alert["telegram_status"] == "queued_not_sent"
    assert alert["email_status"] == "queued_not_sent"
    dashboard = client.get("/api/v1/vendorops/dashboard?tier=starter")
    assert dashboard.status_code == 200
    assert dashboard.json()["kpis"]["active_subscriptions"] == 1
    assert dashboard.json()["kpis"]["monthly_cost_total_usd"] == 12.5

    regenerated = client.post("/api/v1/vendorops/renewal-alerts/generate")
    assert regenerated.status_code == 200
    assert len([item for item in regenerated.json()["alerts"] if item["subscription_id"] == subscription["id"]]) == 1

    reviewed = client.patch(
        f"/api/v1/vendorops/renewal-alerts/{alert['id']}/review",
        json={"explicit_founder_confirmation": True},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["alert"]["delivery_status"] == "reviewed"
    assert client.get("/api/v1/vendorops/renewal-alerts?days=14").json()["alerts"] == []

    canceled = client.post(
        f"/api/v1/vendorops/subscriptions/{subscription['id']}/cancel",
        json={"explicit_founder_confirmation": True},
    )
    assert canceled.status_code == 200
    assert canceled.json()["subscription"]["cancellation_state"] == "founder_confirmed_monitoring"


def test_vendorops_activation_and_crud_flows(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)

    activation = client.get("/api/v1/vendorops/activation")
    assert activation.status_code == 200
    assert activation.json()["activation"]["activation_state"] == "active_free"
    assert activation.json()["checkout_available"] is False

    upgrade = client.post(
        "/api/v1/vendorops/activation/request-upgrade",
        json={"requested_tier": "starter", "explicit_founder_confirmation": True},
    )
    assert upgrade.status_code == 200
    assert upgrade.json()["checkout_available"] is False
    assert upgrade.json()["activation"]["requested_tier"] == "starter"

    account_created = client.post(
        "/api/v1/vendorops/accounts",
        json={
            "tier": "free",
            "vendor_name": "Editable Vendor",
            "category": "software",
            "purpose": "testing",
            "vendor_url": "https://vendor.example",
            "notes": "initial",
            "monthly_cost_usd": 9,
            "renewal_date": "2026-05-01T00:00:00+00:00",
            "credential_ref": "vault://vendorops/editable",
            "credential_owner": "founder",
            "explicit_founder_confirmation": True,
        },
    )
    assert account_created.status_code == 200
    account = account_created.json()["account"]
    assert account["vendor_name"] == "Editable Vendor"
    assert account["credential_ref_masked"] != "vault://vendorops/editable"

    account_updated = client.patch(
        f"/api/v1/vendorops/accounts/{account['id']}",
        json={
            "vendor_name": "Edited Vendor",
            "category": "infra",
            "purpose": "production",
            "vendor_url": "https://edited.example",
            "notes": "edited",
            "monthly_cost_usd": 11,
            "renewal_cadence": "annual",
            "status": "active",
            "credential_owner": "ops",
            "explicit_founder_confirmation": True,
        },
    )
    assert account_updated.status_code == 200
    edited = account_updated.json()["account"]
    assert edited["vendor_name"] == "Edited Vendor"
    assert edited["purpose"] == "production"
    assert edited["credential_owner"] == "ops"

    sub_created = client.post(
        "/api/v1/vendorops/subscriptions",
        json={
            "tier": "free",
            "vendor_name": "Edited Vendor",
            "plan_name": "Free",
            "monthly_cost_usd": 0,
            "renewal_cadence": "monthly",
            "renewal_date": "2026-05-01T00:00:00+00:00",
            "explicit_founder_confirmation": True,
        },
    )
    assert sub_created.status_code == 200
    sub = sub_created.json()["subscription"]

    sub_updated = client.patch(
        f"/api/v1/vendorops/subscriptions/{sub['id']}",
        json={
            "plan_name": "Starter",
            "monthly_cost_usd": 19,
            "renewal_cadence": "monthly",
            "renewal_date": "2026-05-08T00:00:00+00:00",
            "status": "active",
            "explicit_founder_confirmation": True,
        },
    )
    assert sub_updated.status_code == 200
    assert sub_updated.json()["subscription"]["plan_name"] == "Starter"

    audit_events = client.get("/api/v1/vendorops/audit").json()["events"]
    event_types = {event["event_type"] for event in audit_events}
    assert "activation_upgrade_requested" in event_types
    assert "account_updated" in event_types
    assert "subscription_updated" in event_types


def test_vendorops_renewal_alert_buckets(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    now = datetime.now(timezone.utc)
    cases = [
        ("Thirty Vendor", now + timedelta(days=25), "30_day"),
        ("Seven Vendor", now + timedelta(days=5), "7_day"),
        ("One Vendor", now + timedelta(days=1), "1_day"),
        ("Overdue Vendor", now - timedelta(days=2), "overdue"),
    ]
    for vendor, renewal, _bucket in cases:
        response = client.post(
            "/api/v1/vendorops/subscriptions",
            json={
                "tier": "pro",
                "vendor_name": vendor,
                "plan_name": "Pro",
                "monthly_cost_usd": 20,
                "renewal_cadence": "monthly",
                "renewal_date": renewal.isoformat(),
                "explicit_founder_confirmation": True,
            },
        )
        assert response.status_code == 200

    alerts = client.get("/api/v1/vendorops/renewal-alerts?days=30").json()["alerts"]
    by_vendor = {alert["vendor_name"]: alert["alert_type"] for alert in alerts}
    for vendor, _renewal, bucket in cases:
        assert by_vendor[vendor] == bucket


def test_vendorops_checkout_session_scaffold_and_completion(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)

    unavailable = client.post("/api/v1/vendorops/activation/checkout", json={"requested_tier": "starter"})
    assert unavailable.status_code == 200
    assert unavailable.json()["checkout_available"] is False

    class FakeSessionApi:
        @staticmethod
        def create(**_kwargs):
            return {
                "id": "cs_vendorops_test",
                "url": "https://checkout.stripe.test/vendorops",
            }

        @staticmethod
        def retrieve(_session_id):
            return {
                "id": "cs_vendorops_test",
                "payment_status": "paid",
                "subscription": "sub_vendorops_test",
                "customer": "cus_vendorops_test",
                "metadata": {"flow": "vendorops_addon", "vendorops_tier": "starter"},
            }

    class FakeStripe:
        checkout = type("Checkout", (), {"Session": FakeSessionApi})

    monkeypatch.setattr(vendorops_router, "_stripe_client", lambda: FakeStripe)
    monkeypatch.setattr(vendorops_router, "_vendorops_price_id", lambda tier: f"price_{tier}")

    checkout = client.post("/api/v1/vendorops/activation/checkout", json={"requested_tier": "starter", "customer_email": "founder@example.com"})
    assert checkout.status_code == 200
    assert checkout.json()["checkout_available"] is True
    assert checkout.json()["checkout_url"] == "https://checkout.stripe.test/vendorops"
    assert checkout.json()["activation"]["activation_state"] == "active_free"

    completed = client.post("/api/v1/vendorops/activation/checkout-complete", json={"session_id": "cs_vendorops_test"})
    assert completed.status_code == 200
    assert completed.json()["activation"]["activation_state"] == "active_starter"
    assert completed.json()["activation"]["stripe_subscription_id"] == "sub_vendorops_test"


def test_vendorops_alert_delivery_status_transitions(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    renewal = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    created = client.post(
        "/api/v1/vendorops/subscriptions",
        json={
            "tier": "pro",
            "vendor_name": "Delivery Vendor",
            "plan_name": "Pro",
            "monthly_cost_usd": 33,
            "renewal_cadence": "monthly",
            "renewal_date": renewal,
            "explicit_founder_confirmation": True,
        },
    )
    assert created.status_code == 200

    async def fake_telegram(_alert):
        return "sent"

    async def fake_email(_alert):
        return "failed"

    monkeypatch.setattr(vendorops_router, "_deliver_alert_telegram", fake_telegram)
    monkeypatch.setattr(vendorops_router, "_deliver_alert_email", fake_email)

    delivered = client.post("/api/v1/vendorops/renewal-alerts/deliver")
    assert delivered.status_code == 200
    alert = delivered.json()["alerts"][0]
    assert alert["telegram_status"] == "sent"
    assert alert["email_status"] == "failed"
    assert alert["delivery_status"] == "sent"

    delivered_again = client.post("/api/v1/vendorops/renewal-alerts/deliver")
    assert delivered_again.status_code == 200
    assert delivered_again.json()["processed"] == 0


def test_vendorops_approval_listing_and_reject_round_trip(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)

    approval = client.post(
        "/api/v1/vendorops/approvals",
        json={"tier": "starter", "vendor_name": "Rejectable Vendor", "requested_action": "assisted signup"},
    ).json()["approval"]

    listed = client.get("/api/v1/vendorops/approvals?status=pending")
    assert listed.status_code == 200
    assert any(item["id"] == approval["id"] for item in listed.json()["approvals"])

    rejected = client.post(
        f"/api/v1/vendorops/approvals/{approval['id']}/reject",
        json={"explicit_founder_confirmation": True},
    )
    assert rejected.status_code == 200
    assert rejected.json()["approval"]["status"] == "rejected"


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


def test_max_chat_answers_vendorops_queries_from_summary_route(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    renewal = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    client.post(
        "/api/v1/vendorops/subscriptions",
        json={
            "tier": "pro",
            "vendor_name": "MAX Query Vendor",
            "plan_name": "Pro Plan",
            "monthly_cost_usd": 49,
            "renewal_cadence": "monthly",
            "renewal_date": renewal,
            "explicit_founder_confirmation": True,
        },
    )

    response = client.post(
        "/api/v1/max/chat",
        json={
            "message": "VendorOps query only: what tier is active, what renewals are queued, and what is monthly external-services cost?",
            "channel": "web_chat",
            "conversation_id": "test-vendorops-query",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["model_used"] == "vendorops-query"
    assert body["metadata"]["skill_used"] == "vendorops_summary"
    assert body["tool_results"][0]["success"] is True
    assert "VendorOps query result (read-only)" in body["response"]
    assert "Monthly external-services cost: $49.00" in body["response"]
    assert "MAX Query Vendor" in body["response"]


def test_max_chat_blocks_vendorops_write_requests(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)

    response = client.post(
        "/api/v1/max/chat",
        json={
            "message": "VendorOps approve this pending vendor now",
            "channel": "web_chat",
            "conversation_id": "test-vendorops-write-block",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["model_used"] == "vendorops-query"
    assert body["tool_results"][0]["error"] == "write_gate_blocked"
    assert "write request blocked" in body["response"].lower()
