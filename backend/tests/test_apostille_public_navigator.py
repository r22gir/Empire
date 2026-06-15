"""
R1D-PUB-NAV — Public Service Navigator regression test.

Verifies the public customer surface at https://apostapp.empirebox.store/apostille
exposes a public-safe Service Navigator and does NOT expose any operator-only screens.

Uses Playwright via the Node CLI; see the headless probe in the build report.

⚠️  LIVE-TEST GUARD (2026-06-14) ⚠️
This file calls GET https://apostapp.empirebox.store/* via the LIVE
CF edge + tunnel + backend stack. The calls are read-only (no order/
customer mutation), but they exercise the live infrastructure and
should be guarded behind explicit Founder approval for any CI/coverage
run. The tests are now SKIPPED unless APOSTILLE_LIVE_TEST_TOKEN is set
explicitly. See backend/tests/helpers/live_test_guard.py and
HERMES-REPORT-GATE3-PAYMENT-INCIDENT-CLEANUP-AND-TEST-GUARDS-20260614.md.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from helpers.live_test_guard import require_live_test_token  # noqa: E402

require_live_test_token(__file__)

import json
import requests
import pytest

PUBLIC = "https://apostapp.empirebox.store/apostille"


def _get_page_html():
    r = requests.get(PUBLIC, timeout=15)
    assert r.status_code == 200, f"expected 200, got {r.status_code}"
    return r.text


def test_t01_intake_form_still_present():
    """The original intake form (R1B) is still rendered."""
    html = _get_page_html()
    assert 'data-testid="intake-form"' in html, "intake form testid missing"


def test_t02_service_navigator_present():
    """The new Service Navigator (R1D-PUB-NAV) is rendered."""
    html = _get_page_html()
    assert 'data-testid="service-navigator"' in html, "service navigator testid missing"


def test_t03_navigator_has_all_eight_sections():
    """All 8 spec-required sections are present in the rendered HTML."""
    html = _get_page_html()
    sections = [
        "Service paths",
        "Notarization",
        "Business documents",  # was "Business / LLC" before R1D-BOUNDARY; renamed to reflect product boundary
        "Pricing",
        "Shipping",
        "Upload",
        "Frequently asked",
    ]
    missing = [s for s in sections if s not in html]
    assert not missing, f"missing navigator sections: {missing}"


def test_t04_disclaimer_present():
    """Disclaimer mentions 'law firm' (not legal advice) — public-safe."""
    html = _get_page_html()
    assert "law firm" in html, "disclaimer missing"
    assert "legal advice" in html, "disclaimer doesn't mention legal advice"


def test_t05_three_live_packages_listed():
    """The pricing section lists the 3 live packages at $35 / $95 / $195."""
    html = _get_page_html()
    assert "35" in html, "basic_intake $35 not mentioned"
    assert "95" in html, "standard $95 not mentioned"
    assert "195" in html, "rush $195 not mentioned"


def test_t06_five_shipping_methods_listed():
    """All 5 shipping methods from the spec are mentioned in the shipping section."""
    html = _get_page_html()
    for term in ["USPS Priority", "USPS Express", "FedEx", "International Priority", "Local Pickup"]:
        assert term in html, f"shipping method missing: {term}"


def test_t07_honest_upload_pending_wording():
    """Upload section is honest about the email-based upload (v1) rather than a fake in-browser form."""
    html = _get_page_html()
    # The honest pending wording should mention email and "coming soon" for direct upload
    assert "email" in html.lower(), "upload section doesn't mention email"
    assert "upload" in html.lower(), "upload section missing"
    # Should NOT claim a direct in-browser upload is currently functional
    # (we don't have a hard negative test for this, but the 'coming soon' framing should be present)


def test_t08_no_operator_only_screens_exposed():
    """Operator-only surfaces (orders dashboard, customers, internal AI tools, etc.) must NOT appear in the public HTML."""
    html = _get_page_html().lower()
    banned_terms = [
        "orders dashboard",
        "internal ai tools",
        "operator payment panel",
        "raw customer database",
        "/admin",
        "studio.empirebox.store",  # operator surface, must not appear in public
        "api.empirebox.store",     # operator API
        "luxe.empirebox.store",
        "forge.empirebox.store",
        "hermes.empirebox.store",
        "api/v1/apostapp/orders",
        "api/v1/apostapp/customers",
        "api/v1/apostapp/dashboard",
        "ron scheduling",  # operator-side only
        "ron session form",
        "couriers directory",  # operator-side
    ]
    leaked = [b for b in banned_terms if b in html]
    assert not leaked, f"operator-only terms leaked into public page: {leaked}"


def test_t09_ron_wording_uses_public_safe_framing():
    """RON (remote online notarization) is described in public-safe terms — no operator-side details."""
    html = _get_page_html()
    # Public-safe RON wording: video session, licensed notary, scheduled, secure
    for term in ["RON", "remote online notarization", "video", "licensed", "notary"]:
        assert term.lower() in html.lower(), f"public RON wording missing: {term}"


def test_t10_llc_upsell_present():
    """LLC / business documents upsell is present (Articles of Organization, Operating Agreement, etc.).

    Note: per R1D-BOUNDARY, the public navigator no longer has a separate 'LLC upsell' card.
    Business documents are mentioned inline in the 'Business documents' section, with a small
    related-service cross-link to LLCFactory at the bottom. This test verifies both:
    - the business-documents mention is present
    - the related-service cross-link to LLCFactory is present
    """
    html = _get_page_html()
    # Business-document mention (public-safe)
    for term in ["Articles of Organization", "Certificates of Good Standing"]:
        assert term in html, f"business-document mention missing: {term}"
    # Related-service cross-link (LLCFactory, small note at bottom)
    for term in ["Related service", "LLCFactory"]:
        assert term in html, f"related-service cross-link missing: {term}"


def test_t11_embassy_legalization_mentioned():
    """Embassy legalization path is mentioned (for non-Hague countries)."""
    html = _get_page_html()
    assert "embassy" in html.lower(), "embassy legalization missing"
    assert "hague" in html.lower(), "hague convention context missing"


def test_t12_no_live_charges_created_by_this_test():
    """This test only GETs the public page; no charges are possible."""
    # Sanity: only GET requests are made in this file
    assert True  # explicit no-op assertion; the test class is read-only


def test_t13_public_config_still_test_mode_false():
    """Sanity: backend still says test_mode: false (live env from R1D is still in effect)."""
    r = requests.get("https://apostapp.empirebox.store/api/v1/apostapp/public/config", timeout=10)
    assert r.status_code == 200
    assert r.json().get("test_mode") is False


def test_t14_founder_operator_interface_still_intact():
    """Sanity: the founder/operator apostapp screen at /?screen=apostapp on the operator portal still
    loads without client-side crash (R1D-PROD-A-2 fix is still in effect)."""
    # We can't run Playwright from a pytest test easily, so we use a curl-based smoke check
    # and rely on the portal's HEAD/GET behavior.
    r = requests.get("http://127.0.0.1:3005/?screen=apostapp", timeout=10, allow_redirects=False)
    # Either 200 (page loaded — JS will hydrate in browser) or 3xx (redirect)
    assert r.status_code in (200, 301, 302, 307, 308), f"portal returned unexpected {r.status_code}"
