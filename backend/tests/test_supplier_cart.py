"""Supplier cart: prepare → owner yes → job PO. Never live checkout/pay."""
from __future__ import annotations

import importlib
import os

import pytest


def _reload(monkeypatch, tmp_path):
    db = str(tmp_path / "empire.db")
    monkeypatch.setenv("EMPIRE_TASK_DB", db)
    from app.db import database
    importlib.reload(database)
    from app.services.supplier_cart import store, flow
    importlib.reload(store)
    importlib.reload(flow)
    store.ensure_tables()
    assert os.environ["EMPIRE_TASK_DB"] == db
    assert "empire-data" not in db
    return flow, store, db


def test_build_cart_prepares_and_does_not_pay(monkeypatch, tmp_path):
    flow, _, db = _reload(monkeypatch, tmp_path)
    cart = flow.build_cart(
        job_id="job-1",
        supplier_name="Foam House",
        lines=[{"title": "2 inch foam", "qty": "2", "note": "Prepare only"}],
    )
    assert cart["prepared"] is True
    assert cart["checked_out"] is False
    assert cart["paid"] is False
    assert cart["live_charge"] is False
    assert cart["status"] == "prepared"
    assert cart["lines"][0]["title"] == "2 inch foam"
    assert cart["next"] == "owner_approval"
    assert os.environ["EMPIRE_TASK_DB"] == db


def test_approve_without_owner_yes_is_refused(monkeypatch, tmp_path):
    flow, _, _ = _reload(monkeypatch, tmp_path)
    cart = flow.build_cart(job_id="job-1", lines=[{"title": "Walnut", "qty": "1"}])
    with pytest.raises(flow.SupplierCartError, match="explicit yes"):
        flow.approve_cart(cart["id"], owner_yes=False)
    loaded = flow.get_cart(cart["id"])
    assert loaded["status"] == "prepared"
    assert loaded["purchase_orders"] == []
    assert loaded["paid"] is False


def test_owner_yes_creates_po_linked_to_job(monkeypatch, tmp_path):
    flow, _, _ = _reload(monkeypatch, tmp_path)
    cart = flow.build_cart(job_id="job-42", supplier_name="Lumber Yard", lines=[{"title": "Plywood", "qty": "3"}])
    flow.request_owner_approval(cart["id"])
    approved = flow.approve_cart(cart["id"], owner_yes=True)
    assert approved["owner_yes"] is True
    assert approved["status"] == "po_created"
    assert approved["checked_out"] is False
    assert approved["paid"] is False
    po = approved["purchase_order"]
    assert po["job_id"] == "job-42"
    assert po["po_number"].startswith("PO-")
    assert po["paid"] is False
    pos = flow.list_job_purchase_orders("job-42")
    assert len(pos) == 1
    assert pos[0]["job_id"] == "job-42"
    assert pos[0]["cart_id"] == cart["id"]


def test_checkout_and_pay_require_owner_yes_and_never_charge(monkeypatch, tmp_path):
    flow, _, _ = _reload(monkeypatch, tmp_path)
    cart = flow.build_cart(job_id="job-9", lines=[{"title": "Welt", "qty": "1"}])
    with pytest.raises(flow.SupplierCartError, match="Checkout refused"):
        flow.checkout_cart(cart["id"], owner_yes=False)
    with pytest.raises(flow.SupplierCartError, match="Pay refused"):
        flow.pay_cart(cart["id"], owner_yes=False)
    # Even after owner yes, no live charge and paid stays false.
    flow.approve_cart(cart["id"], owner_yes=True)
    checkout = flow.checkout_cart(cart["id"], owner_yes=True)
    pay = flow.pay_cart(cart["id"], owner_yes=True)
    assert checkout["checked_out"] is False
    assert checkout["paid"] is False
    assert checkout["live_charge"] is False
    assert pay["paid"] is False
    assert pay["live_charge"] is False
    assert "not performed" in pay["message"].lower() or "no live" in pay["message"].lower()


def test_organizer_stub_replacement(monkeypatch, tmp_path):
    flow, _, _ = _reload(monkeypatch, tmp_path)
    created = flow.organizer_supplier_cart(
        item={"title": "Marley materials", "job_id": "job-m"},
        extra={"lines": [{"title": "Foam", "qty": "2", "note": "Prepare only"}]},
        job={"id": "job-m"},
    )
    assert created["prepared"] is True
    assert created["checked_out"] is False
    assert created["paid"] is False
    assert created["cart_id"]
    assert created["next"] == "owner_approval"
    assert created["sent"] is False


def test_cart_from_nest_and_api_flow(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))
    from app.db import database
    importlib.reload(database)
    from app.services.supplier_cart import store
    importlib.reload(store)
    store.ensure_tables()
    from app.services.cnc.nesting import nest_cut_list
    nest = nest_cut_list({
        "job_id": "job-nest",
        "parts": [{
            "name": "Side",
            "wood": {"width": "12", "length": "20"},
            "fabric": {"width": "15", "length": "24"},
            "grain": "with",
        }],
    })
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routers import supplier_cart as cart_router
    app = FastAPI()
    app.include_router(cart_router.router, prefix="/api/v1")
    client = TestClient(app)
    built = client.post("/api/v1/supplier-carts/from-nest", json={"nest": nest, "job_id": "job-nest"})
    assert built.status_code == 200, built.text
    cart = built.json()
    assert cart["checked_out"] is False
    assert cart["paid"] is False
    assert any("Plywood" in ln["title"] or "Foam" in ln["title"] or "Fabric" in ln["title"] for ln in cart["lines"])

    denied = client.post(f"/api/v1/supplier-carts/{cart['id']}/approve", json={"owner_yes": False})
    assert denied.status_code == 403

    ok = client.post(
        f"/api/v1/supplier-carts/{cart['id']}/approve",
        json={"owner_yes": True, "job_id": "job-nest"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["purchase_order"]["job_id"] == "job-nest"
    assert ok.json()["paid"] is False

    pay = client.post(f"/api/v1/supplier-carts/{cart['id']}/pay", json={"owner_yes": False})
    assert pay.status_code == 403

    listed = client.get("/api/v1/jobs/job-nest/purchase-orders")
    assert listed.status_code == 200
    assert listed.json()["purchase_orders"][0]["job_id"] == "job-nest"

    stub = client.post("/api/v1/supplier-carts/organizer-action", json={
        "item": {"title": "Build supplier cart", "job_id": "job-org"},
        "lines": [{"title": "Foam", "qty": "2", "note": "Prepare only"}],
    })
    assert stub.status_code == 200
    assert stub.json()["prepared"] is True
    assert stub.json()["paid"] is False
