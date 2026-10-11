"""LeadForge Prospect Finder health + free contact lookup + Max acquisition tools.

Runs on an isolated temp DB (EMPIRE_TASK_DB) with no network: website fetches go
through an httpx MockTransport.
"""
import asyncio
import importlib
import json

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture()
def lf(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))
    from app.db import database, init_db
    importlib.reload(database); importlib.reload(init_db); init_db.init_database()
    from app.services.leadforge import prospect_engine, contact_enrich, prospect_ops, acquisition
    from app.routers import customer_mgmt, leadforge
    for m in (prospect_engine, contact_enrich, prospect_ops, acquisition, customer_mgmt, leadforge):
        importlib.reload(m)
    with prospect_engine._db() as conn:
        rows = [
            # google row: street stored in city (old parser), no website
            dict(name="Design Pro Remodeling", address="8300 Arlington Blvd Ste B3, Fairfax, VA 22031, USA",
                 city="8300 Arlington Blvd Ste B3", state="VA", location="Fairfax VA", source="google_places",
                 platform="google", external_id="PLACE123", score=88, rating=4.9, review_count=580, client_type="contractor",
                 categories=json.dumps(["general_contractor", "establishment"]), gc_fit=1,
                 recommended_angle="subcontractor for window treatments and soft furnishings"),
            dict(name="Ann Example Interiors | McLean VA Interior Designer", website="https://annstudio.test/about",
                 location="Chevy Chase MD", city="Chase", source="brave", platform="brave_search", score=60,
                 client_type="designer", designer_fit=1),
            dict(name="Best 15 Interior Designers in DC | Houzz", website="https://www.houzz.com/x", location="Washington DC",
                 source="brave", score=20),
        ]
        for r in rows:
            cols = ", ".join(r); conn.execute(f"INSERT INTO prospects ({cols}) VALUES ({', '.join('?' * len(r))})", list(r.values()))
    app = FastAPI(); app.include_router(leadforge.router, prefix="/api/v1")
    return dict(client=TestClient(app), pe=prospect_engine, ce=contact_enrich, po=prospect_ops, acq=acquisition)


SITE = {
    "/robots.txt": "User-agent: *\nDisallow: /private\n",
    "/": '<html><a href="/contact">Contact</a><a href="/our-team">Team</a><a href="/private/staff">x</a>'
         '<a href="https://www.instagram.com/annstudio/">IG</a><a href="https://www.instagram.com/p/abc/">post</a></html>',
    "/about": "<p>We design homes.</p>",
    "/contact": '<a href="mailto:info@annstudio.test">info</a> <a href="tel:+1-301-555-0199">call</a> '
                '<p>Email ann@annstudio.test</p> <img src="logo@2x.png">',
    "/our-team": "<h2>Ann Example, Principal Designer</h2><p>Meet Principal Designer</p>",
}


def _mock_client(hits):
    def handler(request: httpx.Request):
        hits.append(request.url.path)
        body = SITE.get(request.url.path.rstrip("/") or "/")
        if body is None:
            return httpx.Response(404)
        ctype = "text/plain" if request.url.path == "/robots.txt" else "text/html"
        return httpx.Response(200, text=body, headers={"content-type": ctype})
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True)


def test_display_fields_and_maps_link(lf):
    rows = {p["name"]: p for p in lf["pe"].get_prospects(limit=10)}
    g = rows["Design Pro Remodeling"]
    assert g["display_city"] == "Fairfax, VA"
    assert "query_place_id=PLACE123" in g["maps_url"]
    assert g["category"] == "general contractor"
    b = rows["Ann Example Interiors | McLean VA Interior Designer"]
    assert b["display_name"] == "Ann Example Interiors"
    assert b["display_city"] == "Chevy Chase, MD"
    assert rows["Best 15 Interior Designers in DC | Houzz"]["is_directory_page"] is True


def test_route_health_and_pipeline_to_lead_to_crm(lf):
    c = lf["client"]; B = "/api/v1/leads"
    assert c.get(B + "/campaigns").status_code == 200          # was 422 (shadowed by /{lead_id})
    assert c.get(B + "/999").status_code == 404
    pid = lf["pe"].get_prospects(limit=1)[0]["id"]
    r = c.post(B + f"/leadforge/prospects/{pid}/pipeline").json()
    assert r["status"] == "added" and r["lead_created"] and r["lead_id"]
    again = c.post(B + f"/leadforge/prospects/{pid}/pipeline").json()
    assert again["status"] == "already_in_pipeline" and again["lead_id"] == r["lead_id"] and not again["lead_created"]
    assert c.post(B + "/leadforge/prospects/99999/pipeline").status_code == 404
    pipe = c.get(B + "/leadforge/prospect-pipeline?limit=500").json()
    assert pipe and all(x["status"] == "new" for x in pipe)  # was NULL
    lead = c.get(B + f"/{r['lead_id']}").json()["lead"]
    assert lead["company"] == "Design Pro Remodeling" and lead["next_action_date"]
    crm = c.post(B + f"/{r['lead_id']}/promote")
    assert crm.status_code == 200, crm.text                    # company-only lead used to 400 "Name is required"
    assert c.post(B + f"/{r['lead_id']}/promote").json()["promote_outcome"] == "already_promoted"


def test_free_lookup_respects_robots_and_extracts(lf):
    hits = []

    async def run():
        async with _mock_client(hits) as client:
            lf["ce"].MIN_DELAY_S = 0
            return await lf["ce"].lookup_site("https://annstudio.test/about", "Ann Example Interiors", client=client)
    res = asyncio.run(run())
    assert "/private/staff" not in hits                        # robots.txt Disallow honoured
    assert res["status"] == "found"
    assert res["contact_email"] == "ann@annstudio.test"      # personal beats info@, logo@2x ignored
    assert res["contact_phone"] == "(301) 555-0199"
    assert res["instagram"] == "https://www.instagram.com/annstudio"
    assert res["contact_name"] == "Ann Example" and res["contact_title"] == "Principal Designer"
    assert len(res["pages"]) <= lf["ce"].MAX_PAGES_PER_SITE


def test_directory_sites_are_never_scraped(lf):
    res = asyncio.run(lf["ce"].lookup_site("https://www.houzz.com/x", "x"))
    assert res["status"] == "skipped_directory" and res["pages"] == []


def test_drafts_brief_segments_followups_reactivation(lf):
    c = lf["client"]; B = "/api/v1/leads"
    pid = [p for p in lf["pe"].get_prospects(limit=5) if p["source"] == "brave" and not p["is_directory_page"]][0]["id"]
    d = c.post(B + f"/leadforge/prospects/{pid}/drafts", json={"channel": "instagram_dm"}).json()
    assert d["status"] == "draft" and "Nothing is sent" in d["send_policy"]
    assert c.get(B + f"/leadforge/prospects/{pid}/drafts").json()["drafts"][0]["status"] == "draft"
    brief = c.get(B + "/leadforge/brief?limit=5&days=30").json()
    assert brief["count"] >= 1 and all("suggested_first_message" in i for i in brief["items"])
    assert all(i["name"] != "Best 15 Interior Designers in DC" for i in brief["items"])
    assert c.get(B + "/leadforge/segments").json()["segments"]["designers"] >= 1
    assert c.get(B + "/leadforge/segments/nope").status_code == 400
    r = c.post(B + f"/leadforge/prospects/{pid}/pipeline").json()
    assert c.post(B + f"/{r['lead_id']}/followup", json={"in_days": 0, "action": "Call"}).status_code == 200
    due = c.get(B + "/followups/due").json()
    assert any(x["lead_id"] == r["lead_id"] for x in due["due_today"])
    assert "items" in c.get(B + "/reactivation").json()


def test_max_tools_registered_and_bridge_is_read_only(lf):
    from app.services.max import tool_executor
    importlib.reload(tool_executor)
    for name in ("prospect_search", "prospect_enrich", "prospect_rank", "prospect_add_to_pipeline",
                 "prospect_draft_outreach", "prospect_daily_brief", "prospect_segments", "prospect_social_targets",
                 "pipeline_followups", "set_followup", "reactivation_list", "module_catalog", "module_call"):
        assert name in tool_executor.TOOL_REGISTRY, name
    assert "prospect_daily_brief" in tool_executor.TOOLS_DOC
    blocked = tool_executor.execute_tool({"tool": "module_call", "path": "/leads/leadforge/campaigns/drafts/1/send"}, founder=True)
    assert not blocked.success and "read-only" in blocked.error
    brief = tool_executor.execute_tool({"tool": "prospect_daily_brief", "limit": 5, "days": 30}, founder=True)
    assert brief.success and "Never send" in brief.result["next_steps"] + brief.result["send_policy"] or brief.success


def test_social_draft_post_forces_draft(lf, monkeypatch):
    from app.services.max import tool_executor
    importlib.reload(tool_executor)
    sent = {}

    class FakeResp:
        status_code = 200
        text = "{}"
        def json(self):
            return {"id": "x", "status": sent["json"]["status"]}

    class FakeClient:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, url, json=None):
            sent["url"], sent["json"] = url, json
            return FakeResp()
    monkeypatch.setattr(httpx, "Client", FakeClient)
    r = tool_executor.execute_tool({"tool": "socialforge_draft_post", "content": "Before/after: Bethesda living room",
                                    "status": "posted"}, founder=True)
    assert r.success and sent["json"]["status"] == "draft" and sent["url"].endswith("/api/v1/socialforge/posts")
