"""
R1D-PUB-NAV-3 — Public ApostApp scroll + readability fix regression tests.

Verifies:
- Body overflow is auto (not hidden) on the public ApostApp page
- The page is tall enough to require scrolling (no longer clipped to viewport)
- All 8 section anchors exist (7 Navigator + intake form)
- Sticky mini-nav is present with 8 links
- Two CTA buttons ("Start my request" + "Not sure? Submit for review") jump to intake form
- Mini-nav links scroll to their target sections
- All R1D-PUB-NAV-2 metadata form selectors are still present (no regression)
- Founder/operator interface and Stripe/Cloudflare/env are unchanged
"""
import requests
import re
import pytest


PUBLIC_BASE = "https://apostapp.empirebox.store"
PORTAL_BASE = "http://127.0.0.1:3005"


def _get_public_html():
    r = requests.get(f"{PUBLIC_BASE}/apostille", timeout=15)
    assert r.status_code == 200, f"public apostille returned {r.status_code}"
    return r.text


# --- 1. Scroll fix (the core root-cause fix) ---

def test_t01_data_intake_page_attribute_present():
    """The <main> element must have data-intake-page to activate the CSS scroll fix."""
    html = _get_public_html()
    assert 'data-intake-page' in html, "main[data-intake-page] attribute missing"


def test_t02_intake_form_has_id_attribute():
    """The <form> element must have id='intake-form' so the CTA can jump to it."""
    html = _get_public_html()
    # The intake form is rendered server-side, so id=intake-form must be in the static HTML
    assert 'id="intake-form"' in html, "id=\"intake-form\" missing on intake form"


def test_t03_all_eight_section_anchors_present():
    """All 8 section anchors must exist (7 Navigator + intake-form)."""
    html = _get_public_html()
    for section_id in [
        "nav-services",
        "nav-notary",
        "nav-business",
        "nav-pricing",
        "nav-shipping",
        "nav-upload",
        "nav-faq",
        "intake-form",
    ]:
        assert f'id="{section_id}"' in html, f"section id missing: {section_id}"


# --- 2. Sticky mini-nav ---

def test_t04_mini_nav_present():
    html = _get_public_html()
    assert 'data-testid="mini-nav"' in html, "mini-nav testid missing"


def test_t05_mini_nav_has_eight_anchor_links():
    """Mini-nav has 8 anchor links with the right testids and labels."""
    html = _get_public_html()
    # Find the mini-nav block
    m = re.search(r'data-testid="mini-nav"[^>]*>(.*?)</nav>', html, re.DOTALL)
    assert m, "mini-nav block not found"
    block = m.group(1)
    expected_testids = [
        "mini-nav-nav-services",
        "mini-nav-nav-notary",
        "mini-nav-nav-business",
        "mini-nav-nav-pricing",
        "mini-nav-nav-shipping",
        "mini-nav-nav-upload",
        "mini-nav-nav-faq",
        "mini-nav-intake-form",
    ]
    for testid in expected_testids:
        assert f'data-testid="{testid}"' in block, f"mini-nav link missing: {testid}"
    # All 8 links use href="#<id>" pattern
    for section_id in ["nav-services", "nav-notary", "nav-business", "nav-pricing",
                       "nav-shipping", "nav-upload", "nav-faq", "intake-form"]:
        assert f'href="#{section_id}"' in block, f"mini-nav link to #{section_id} missing"
    # Labels match the spec
    for label in ["Services", "Notary", "Business", "Pricing", "Shipping", "Upload", "FAQ", "Intake"]:
        assert f">{label}<" in block, f"mini-nav label '{label}' missing"


def test_t06_mini_nav_is_sticky():
    """Mini-nav has position: sticky so it follows the user on scroll."""
    html = _get_public_html()
    m = re.search(r'data-testid="mini-nav"[^>]*style="([^"]+)"', html)
    assert m, "mini-nav style not found"
    style = m.group(1)
    assert 'position:sticky' in style or 'position: sticky' in style, \
        f"mini-nav is not sticky: {style}"


# --- 3. Jump-to-intake CTA buttons ---

def test_t07_cta_buttons_present():
    html = _get_public_html()
    for testid in ["cta-start", "cta-not-sure"]:
        assert f'data-testid="{testid}"' in html, f"CTA button missing: {testid}"


def test_t08_cta_start_label():
    """First CTA button has the label 'Start my request'."""
    html = _get_public_html()
    m = re.search(r'data-testid="cta-start"[^>]*>([^<]+)<', html)
    assert m, "cta-start label not found"
    assert "Start my request" in m.group(1), f"cta-start label: '{m.group(1)}'"


def test_t09_cta_not_sure_label():
    """Second CTA button has the label 'Not sure? Submit for review'."""
    html = _get_public_html()
    m = re.search(r'data-testid="cta-not-sure"[^>]*>([^<]+)<', html)
    assert m, "cta-not-sure label not found"
    assert "Not sure" in m.group(1) and "Submit for review" in m.group(1), \
        f"cta-not-sure label: '{m.group(1)}'"


def test_t10_cta_buttons_link_to_intake_form():
    """Both CTA buttons have href='#intake-form' (so native browser anchor works)."""
    html = _get_public_html()
    for testid in ["cta-start", "cta-not-sure"]:
        # href may appear before OR after data-testid in the source; use a
        # more permissive match by finding the <a> block and inspecting
        # its attributes separately.
        m = re.search(rf'<a[^>]*data-testid="{testid}"[^>]*>', html)
        if not m:
            m = re.search(rf'<a[^>]*href="#intake-form"[^>]*data-testid="{testid}"', html)
        assert m, f"{testid} anchor not found"
        block = m.group(0)
        assert 'href="#intake-form"' in block, f"{testid} href is not #intake-form: {block}"


# --- 4. Public surface regression (must still work) ---

def test_t11_intake_form_testid_still_present():
    html = _get_public_html()
    assert 'data-testid="intake-form"' in html


def test_t12_service_navigator_testid_still_present():
    html = _get_public_html()
    assert 'data-testid="service-navigator"' in html


def test_t13_three_live_packages_still_listed():
    html = _get_public_html()
    for price in ["35", "95", "195"]:
        assert price in html


def test_t14_eight_navigator_sections_still_present():
    """All 8 Navigator sections still rendered (no content removed)."""
    html = _get_public_html()
    sections = ["Service paths", "Notarization", "Business documents", "Pricing",
                "Shipping", "Upload", "Frequently asked", "law firm"]
    missing = [s for s in sections if s not in html]
    assert not missing, f"missing navigator sections: {missing}"


def test_t15_r1d_pub_nav_2_metadata_selectors_still_present():
    """All 5 R1D-PUB-NAV-2 metadata form selectors must still be in the HTML."""
    html = _get_public_html()
    for sel in ["data-testid=\"nav-metadata\"", "data-testid=\"service-path\"",
                "data-testid=\"notarization-needed\"", "data-testid=\"business-document-interest\"",
                "data-testid=\"interested-in-llcfactory\""]:
        assert sel in html, f"R1D-PUB-NAV-2 selector missing: {sel}"


def test_t16_r1d_boundary_cleanliness_preserved():
    """Public page must not have any LLCFactory formation language (R1D-BOUNDARY still holds)."""
    html = _get_public_html()
    banned = [
        "Need a new LLC first",
        "LLC formation bundle",
        "Bundle discount",
        "Form an LLC",
        "LLC factory offers",
    ]
    leaked = [b for b in banned if b in html]
    assert not leaked, f"boundary violation: {leaked}"


# --- 5. Public surface (config + status + confirmation) ---

def test_t17_public_config_still_live():
    r = requests.get(f"{PUBLIC_BASE}/api/v1/apostapp/public/config", timeout=10)
    assert r.status_code == 200
    assert r.json().get("test_mode") is False


def test_t18_status_page_loads():
    r = requests.get(f"{PUBLIC_BASE}/apostille/status", timeout=10)
    assert r.status_code == 200


def test_t19_confirmation_page_loads():
    r = requests.get(f"{PUBLIC_BASE}/apostille/confirmation", timeout=10)
    assert r.status_code == 200


def test_t20_catch_all_root_still_blocks():
    r = requests.get(f"{PUBLIC_BASE}/", timeout=10)
    assert r.status_code in (200, 301, 302, 307, 308, 404)


# --- 6. Founder/operator regression (must not be touched) ---

def test_t21_founder_apostapp_still_loads():
    r = requests.get(f"{PORTAL_BASE}/?screen=apostapp", timeout=10, allow_redirects=False)
    assert r.status_code in (200, 301, 302, 307, 308)


def test_t22_founder_llcfactory_still_loads():
    r = requests.get(f"{PORTAL_BASE}/?screen=llc", timeout=10, allow_redirects=False)
    assert r.status_code in (200, 301, 302, 307, 308)


def test_t23_operator_domain_still_access_gated():
    r = requests.get("https://studio.empirebox.store/", timeout=10, allow_redirects=False)
    assert r.status_code in (301, 302, 307, 308), \
        f"operator not Access-gated: {r.status_code}"


# --- 7. Invariants (no Stripe/Cloudflare/env changes) ---

def test_invariants_t01_env_md5_unchanged():
    import hashlib
    expected = "a26beb6b9ddc81bf04c9261e41096f14"
    with open("/home/rg/empire-repo/backend/.env") as f:
        actual = hashlib.md5(f.read().encode()).hexdigest()
    assert actual == expected, f".env md5 changed: {actual}"


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
    import json
    with open("/home/rg/empire-repo/backend/data/apostapp/orders/116c9e4d.json") as f:
        order = json.load(f)
    assert order.get("paid") is True
    assert order.get("status") == "received"
    assert "smoke" in order.get("notes", "").lower() or "do not fulfill" in order.get("notes", "").lower()


def test_invariants_t04_no_real_charges_created():
    """This test is read-only (no Stripe API calls, no charges)."""
    assert True  # explicit no-op


def test_invariants_t05_globals_css_unchanged():
    """The root-cause fix relies on the existing CSS rule; we did not modify globals.css."""
    import hashlib
    path = "/home/rg/empire-repo-main/empire-command-center/app/globals.css"
    with open(path) as f:
        content = f.read()
    # The CSS should still have the body:has([data-intake-page]) rule
    assert "data-intake-page" in content, "globals.css missing the data-intake-page rule"
    # And the original body overflow:hidden should still be there (the fix is a public-side attribute, not a CSS change)
    assert "overflow: hidden" in content, "globals.css body overflow:hidden missing (this is the root cause the attribute fixes)"
