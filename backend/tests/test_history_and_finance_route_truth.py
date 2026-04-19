from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _routes_for(path: str, method: str = "GET") -> list:
    return [
        route
        for route in app.routes
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set())
    ]


def test_telegram_history_endpoint_is_labeled_telegram_only():
    res = client.get("/api/v1/max/telegram/history")

    assert res.status_code == 200
    data = res.json()
    assert data["scope"] == "telegram_only"
    assert data["canonical_channel"] == "telegram"
    assert data["unified_history_route"] == "/api/v1/chats/memory-bank?channel=all"
    assert "chats" in data


def test_finance_legacy_routes_are_not_shadowing_canonical_finance():
    dashboard_routes = _routes_for("/api/v1/finance/dashboard")
    payment_routes = _routes_for("/api/v1/finance/payments")
    legacy_dashboard_routes = _routes_for("/api/v1/finance-legacy/dashboard")
    legacy_payment_routes = _routes_for("/api/v1/finance-legacy/payments")

    assert len(dashboard_routes) == 1
    assert dashboard_routes[0].endpoint.__module__ == "app.routers.finance"
    assert len(payment_routes) == 1
    assert payment_routes[0].endpoint.__module__ == "app.routers.finance"
    assert len(legacy_dashboard_routes) == 1
    assert legacy_dashboard_routes[0].endpoint.__module__ == "app.routers.financial"
    assert len(legacy_payment_routes) == 1
    assert legacy_payment_routes[0].endpoint.__module__ == "app.routers.financial"


def test_stripe_webhook_primary_and_legacy_ownership_is_explicit():
    primary = _routes_for("/api/v1/payments/webhook", method="POST")
    legacy_stripe = _routes_for("/webhooks/stripe", method="POST")
    legacy_nested = _routes_for("/webhooks/webhooks/stripe", method="POST")

    assert len(primary) == 1
    assert primary[0].endpoint.__module__ == "app.routers.payments"
    assert len(legacy_stripe) == 1
    assert legacy_stripe[0].endpoint.__module__ == "app.routers.webhooks"
    assert len(legacy_nested) == 1
    assert legacy_nested[0].endpoint.__module__ == "app.routers.webhooks"
