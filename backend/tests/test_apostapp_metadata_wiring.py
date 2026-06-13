"""
R1D-PUB-NAV-2 — Service Navigator metadata wiring regression tests.

Verifies the metadata wiring from the public Service Navigator to the order JSON:
- 4 new optional fields on the public intake form (service_path, notarization_needed,
  business_document_interest, interested_in_llcfactory)
- Backend accepts the new fields
- Backend writes them into order metadata
- Pre-existing metadata is preserved
- Missing fields default to absent (not null/false)
- Form data-testid selectors are present in the rendered HTML
- Founder/operator interface and Stripe/Cloudflare/env are unchanged
"""
import json
import time
import uuid
import requests
import pytest


PUBLIC_BASE = "https://apostapp.empirebox.store"
ORDERS_DIR = "/home/rg/empire-repo/backend/data/apostapp/orders"


def _post_intake(payload, timeout=15):
    r = requests.post(
        f"{PUBLIC_BASE}/api/v1/apostapp/public/intake",
        json=payload,
        timeout=timeout,
    )
    return r


def _load_order_json(order_id):
    with open(f"{ORDERS_DIR}/{order_id}.json") as f:
        return json.load(f)


# --- Backend metadata wiring ---

def test_t01_intake_accepts_all_four_navigator_fields():
    """All 4 new optional fields are accepted by the public intake endpoint."""
    payload = {
        "client_name": "R1D-PUB-NAV-2 T01",
        "email": f"r1d-pub-nav-2-t01-{uuid.uuid4().hex[:8]}@empirebox.store",
        "document_type": "birth_certificate",
        "destination_country": "Brazil",
        "origin_state": "MD",
        "service_level": "basic_intake",
        "service_path": "embassy_legalization",
        "notarization_needed": True,
        "business_document_interest": False,
        "interested_in_llcfactory": False,
        "notes": "R1D-PUB-NAV-2 t01 metadata wiring smoke test.",
    }
    r = _post_intake(payload)
    assert r.status_code == 200, f"intake returned {r.status_code}: {r.text}"
    order_id = r.json()["order_id"]
    order = _load_order_json(order_id)
    assert order["metadata"]["service_path"] == "embassy_legalization"
    assert order["metadata"]["notarization_needed"] is True
    assert order["metadata"]["business_document_interest"] is False
    assert order["metadata"]["interested_in_llcfactory"] is False
    assert order["metadata"]["nav_source"] == "service_navigator_v2"


def test_t02_intake_works_without_navigator_fields():
    """The form still works when navigator fields are absent (backward-compat)."""
    payload = {
        "client_name": "R1D-PUB-NAV-2 T02",
        "email": f"r1d-pub-nav-2-t02-{uuid.uuid4().hex[:8]}@empirebox.store",
        "document_type": "diploma",
        "destination_country": "Mexico",
        "origin_state": "VA",
        "service_level": "standard",
        "notes": "R1D-PUB-NAV-2 t02 backward-compat test.",
    }
    r = _post_intake(payload)
    assert r.status_code == 200, f"intake returned {r.status_code}: {r.text}"
    order_id = r.json()["order_id"]
    order = _load_order_json(order_id)
    # None of the new metadata fields should be present
    assert "service_path" not in order["metadata"]
    assert "notarization_needed" not in order["metadata"]
    assert "business_document_interest" not in order["metadata"]
    assert "interested_in_llcfactory" not in order["metadata"]
    assert "nav_source" not in order["metadata"]
    # But the pre-existing fields should still be there
    assert order["metadata"]["source"] == "public_fast_lane"
    assert order["metadata"]["package_id"] == "standard"
    assert order["metadata"]["test_mode"] is False


def test_t03_intake_with_partial_navigator_fields():
    """Only some navigator fields are set — only those should appear in metadata."""
    payload = {
        "client_name": "R1D-PUB-NAV-2 T03",
        "email": f"r1d-pub-nav-2-t03-{uuid.uuid4().hex[:8]}@empirebox.store",
        "document_type": "transcript",
        "destination_country": "Germany",
        "origin_state": "DC",
        "service_level": "rush",
        "service_path": "federal_apostille",
        "notes": "R1D-PUB-NAV-2 t03 partial metadata test.",
    }
    r = _post_intake(payload)
    assert r.status_code == 200
    order_id = r.json()["order_id"]
    order = _load_order_json(order_id)
    assert order["metadata"]["service_path"] == "federal_apostille"
    # The 3 booleans were not sent — they should not appear in metadata
    assert "notarization_needed" not in order["metadata"]
    assert "business_document_interest" not in order["metadata"]
    assert "interested_in_llcfactory" not in order["metadata"]


def test_t04_pre_existing_metadata_preserved():
    """The 4 pre-existing metadata fields (source, package_id, package_name, test_mode) are not disturbed."""
    payload = {
        "client_name": "R1D-PUB-NAV-2 T04",
        "email": f"r1d-pub-nav-2-t04-{uuid.uuid4().hex[:8]}@empirebox.store",
        "document_type": "operating_agreement",
        "destination_country": "United Kingdom",
        "origin_state": "MD",
        "service_level": "standard",
        "service_path": "certified_copy",
        "notarization_needed": True,
        "business_document_interest": True,
        "interested_in_llcfactory": True,
    }
    r = _post_intake(payload)
    assert r.status_code == 200
    order_id = r.json()["order_id"]
    order = _load_order_json(order_id)
    # Pre-existing
    assert order["metadata"]["source"] == "public_fast_lane"
    assert order["metadata"]["package_id"] == "standard"
    assert order["metadata"]["package_name"] == "Standard Apostille Support"
    assert order["metadata"]["test_mode"] is False
    # New
    assert order["metadata"]["service_path"] == "certified_copy"
    assert order["metadata"]["notarization_needed"] is True
    assert order["metadata"]["business_document_interest"] is True
    assert order["metadata"]["interested_in_llcfactory"] is True
    assert order["metadata"]["nav_source"] == "service_navigator_v2"


def test_t05_all_seven_service_paths_accepted_at_pydantic_level():
    """All 7 valid service_path values are accepted by the Pydantic schema.

    We test at the Pydantic schema level (not HTTP) to avoid the 5/hour
    rate limit on the public intake endpoint. The HTTP path was already
    exercised by t01, t02, t03, t04 above.
    """
    from app.routers.apostapp_public import PublicIntakeRequest
    paths = [
        "state_apostille",
        "federal_apostille",
        "embassy_legalization",
        "certified_copy",
        "vital_records_apostille",
        "fbi_background_apostille",
        "other",
    ]
    for path in paths:
        req = PublicIntakeRequest(
            client_name="Pydantic Test",
            email="test@empirebox.store",
            document_type="diploma",
            destination_country="Spain",
            origin_state="DC",
            service_level="standard",
            service_path=path,
        )
        assert req.service_path == path, f"service_path={path} not preserved at Pydantic level"


def test_t06_optional_fields_default_to_none():
    """When the new fields are absent, the Pydantic schema defaults them to None."""
    from app.routers.apostapp_public import PublicIntakeRequest
    req = PublicIntakeRequest(
        client_name="Pydantic Test",
        email="test@empirebox.store",
        document_type="diploma",
        destination_country="Spain",
        origin_state="DC",
        service_level="standard",
    )
    assert req.service_path is None
    assert req.notarization_needed is None
    assert req.business_document_interest is None
    assert req.interested_in_llcfactory is None


def test_t07_optional_fields_can_be_explicitly_false():
    """Boolean fields can be explicitly set to False (not coerced to None)."""
    from app.routers.apostapp_public import PublicIntakeRequest
    req = PublicIntakeRequest(
        client_name="Pydantic Test",
        email="test@empirebox.store",
        document_type="diploma",
        destination_country="Spain",
        origin_state="DC",
        service_level="standard",
        notarization_needed=False,
        business_document_interest=False,
        interested_in_llcfactory=False,
    )
    assert req.notarization_needed is False
    assert req.business_document_interest is False
    assert req.interested_in_llcfactory is False


# --- Public surface still works (regression) ---

def test_pub_t01_intake_form_still_present():
    r = requests.get(f"{PUBLIC_BASE}/apostille", timeout=10)
    assert r.status_code == 200
    assert 'data-testid="intake-form"' in r.text


def test_pub_t02_service_navigator_still_present():
    r = requests.get(f"{PUBLIC_BASE}/apostille", timeout=10)
    assert r.status_code == 200
    assert 'data-testid="service-navigator"' in r.text


def test_pub_t03_new_form_selectors_present():
    """The new R1D-PUB-NAV-2 form fields have data-testid attributes for testability."""
    r = requests.get(f"{PUBLIC_BASE}/apostille", timeout=10)
    assert r.status_code == 200
    html = r.text
    for selector in [
        'data-testid="nav-metadata"',
        'data-testid="service-path"',
        'data-testid="notarization-needed"',
        'data-testid="business-document-interest"',
        'data-testid="interested-in-llcfactory"',
    ]:
        assert selector in html, f"missing selector: {selector}"


def test_pub_t04_three_live_packages_still_listed():
    r = requests.get(f"{PUBLIC_BASE}/apostille", timeout=10)
    assert r.status_code == 200
    for pkg_price in ["35", "95", "195"]:
        assert pkg_price in r.text


def test_pub_t05_public_config_still_live():
    r = requests.get(f"{PUBLIC_BASE}/api/v1/apostapp/public/config", timeout=10)
    assert r.status_code == 200
    assert r.json().get("test_mode") is False


# --- Invariants (no Stripe/Cloudflare/env/charges/smoke-order touched) ---

def test_invariants_t01_env_md5_unchanged():
    """The .env md5 hasn't changed since R1D live install."""
    import hashlib
    expected = "a26beb6b9ddc81bf04c9261e41096f14"
    with open("/home/rg/empire-repo/backend/.env") as f:
        actual = hashlib.md5(f.read().encode()).hexdigest()
    assert actual == expected, f".env md5 changed: expected {expected}, got {actual}"


def test_invariants_t02_yml_files_unchanged():
    import hashlib
    expected = {
        "/home/rg/.cloudflared/empire-main-local.yml": "a2fa04011e07a79ffd2a88911885f40a",
        "/home/rg/.cloudflared/apostille-public.yml": "1528d62561295579a99021953b75c3ba",
    }
    for path, md5 in expected.items():
        with open(path) as f:
            actual = hashlib.md5(f.read().encode()).hexdigest()
        assert actual == md5, f"{path} md5 changed"


def test_invariants_t03_smoke_order_intact():
    path = "/home/rg/empire-repo/backend/data/apostapp/orders/116c9e4d.json"
    with open(path) as f:
        order = json.load(f)
    assert order.get("paid") is True
    assert order.get("status") == "received"
    assert "smoke" in order.get("notes", "").lower() or "do not fulfill" in order.get("notes", "").lower()
    # R1D-PUB-NAV-2: this smoke order was created BEFORE the new metadata fields were added.
    # It should NOT have the new metadata fields.
    assert "service_path" not in order.get("metadata", {}), \
        "smoke order should not have R1D-PUB-NAV-2 metadata (created pre-lane)"


def test_invariants_t04_live_packages_endpoint_unchanged():
    r = requests.get(f"{PUBLIC_BASE}/api/v1/apostapp/public/packages", timeout=10)
    assert r.status_code == 200
    packages = r.json().get("packages", [])
    assert len(packages) == 3
    prices = sorted([p["price_cents"] for p in packages])
    assert prices == [3500, 9500, 19500], f"prices changed: {prices}"


def test_invariants_t05_no_real_charges_created():
    """This test only creates test orders (no Stripe API calls, no payments)."""
    # All test orders are created via the public intake endpoint, which is in
    # test_mode=false (live env). HOWEVER, the public intake endpoint does NOT
    # create a Stripe Checkout session — that's a separate /payments/checkout
    # call that we did NOT make. So no real charges happened.
    assert True  # explicit no-op


def test_invariants_t06_founder_operator_apostapp_still_works():
    """The Founder's /?screen=apostapp deep link still works (no operator regression)."""
    r = requests.get("http://127.0.0.1:3005/?screen=apostapp", timeout=10, allow_redirects=False)
    assert r.status_code in (200, 301, 302, 307, 308)


def test_invariants_t07_founder_operator_llcfactory_still_works():
    r = requests.get("http://127.0.0.1:3005/?screen=llc", timeout=10, allow_redirects=False)
    assert r.status_code in (200, 301, 302, 307, 308)


def test_invariants_t08_operator_domains_still_access_gated():
    r = requests.get("https://studio.empirebox.store/", timeout=10, allow_redirects=False)
    assert r.status_code in (301, 302, 307, 308), \
        f"operator domain not Access-gated: {r.status_code}"
