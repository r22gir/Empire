"""
iX-day R1X-INT-FIX: Golden-path E2E for the LuxeForge client intake.

Encodes the full client journey per the fix dispatch brief:

  1. Anonymous page load on the production door (Next.js portal)
  2. Quick signup via /api/v1/intake/signup
  3. Submit an item request with an image attachment
  4. Row lands in /home/rg/empire-data/empire.db intake_projects WITH
     business='workroom' (Doctrine #4)
  5. Founder's LuxeForge admin page lists it via /api/v1/intake/admin/projects

Per CLAUDE.md model-independence doctrine: this test is the lifecycle
insurance against regression of the 2026-08-05 sev (zero organic
submissions since 2026-06-05; 4 severed bridges). If any of these
steps breaks, the test fails and the founder knows.

Runs against the LIVE backend on http://127.0.0.1:8000 and the LIVE
Next.js portal on http://127.0.0.1:3005. The portal host test is
parametrized over the production hostname (luxe.empirebox.store) so
the same script can be re-run from the real public URL once the CF
Access bypass is live (separate dispatch).

Requirements:
  - empire-backend running on :8000 (PID 1 worker)
  - empire-portal running on :3005 (env: backend upstream = :8000)
  - pytest (any modern version)
"""
import os
import sys
import time
import uuid
from pathlib import Path
import sqlite3
import urllib.request
import urllib.error
import json

import pytest

# Use the local venv's requests if available, fall back to stdlib urllib
try:
    import requests  # noqa: F401
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


BACKEND = os.getenv("EMPIRE_BACKEND_URL", "http://127.0.0.1:8000")
PORTAL = os.getenv("EMPIRE_PORTAL_URL", "http://127.0.0.1:3005")
EMPIRE_DB = "/home/rg/empire-data/empire.db"


def _http(method, url, *, headers=None, data=None, files=None, timeout=10, allow_redirects=False):
    """Minimal HTTP helper so this test runs without `requests`."""
    if HAS_REQUESTS:
        if files:
            return requests.request(method, url, headers=headers, data=data, files=files, timeout=timeout, allow_redirects=allow_redirects)
        body = json.dumps(data).encode() if data is not None else None
        h = {"Content-Type": "application/json", **(headers or {})}
        return requests.request(method, url, headers=h, data=body, timeout=timeout, allow_redirects=allow_redirects)
    # Fallback: urllib
    if files:
        # Build multipart manually
        boundary = uuid.uuid4().hex
        body = b""
        for k, v in (data or {}).items():
            body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
        for fk, (fname, fcontent, ftype) in files.items():
            body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{fk}\"; filename=\"{fname}\"\r\nContent-Type: {ftype}\r\n\r\n".encode()
            body += fcontent + b"\r\n"
        body += f"--{boundary}--\r\n".encode()
        h = {"Content-Type": f"multipart/form-data; boundary={boundary}", **(headers or {})}
        req = urllib.request.Request(url, data=body, headers=h, method=method)
    else:
        body = json.dumps(data).encode() if data is not None else None
        h = {"Content-Type": "application/json", **(headers or {})}
        req = urllib.request.Request(url, data=body, headers=h, method=method)
    # Custom opener that does NOT follow redirects
    if not allow_redirects:
        class _NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None
        opener = urllib.request.build_opener(_NoRedirect())
        try:
            with opener.open(req, timeout=timeout) as resp:
                return _StdResponse(resp.status, resp.read())
        except urllib.error.HTTPError as e:
            return _StdResponse(e.code, e.read())
    # allow_redirects=True (default urllib behavior)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return _StdResponse(resp.status, resp.read())
    except urllib.error.HTTPError as e:
        return _StdResponse(e.code, e.read())


class _StdResponse:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body
    def json(self):
        return json.loads(self._body)
    @property
    def text(self):
        return self._body.decode(errors="replace")


def _create_founder_admin(email, password):
    """Insert a founder admin directly into empire.db so the test can
    verify the admin-list endpoint. Returns the user_id."""
    from passlib.context import CryptContext
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    user_id = str(uuid.uuid4())
    conn = sqlite3.connect(EMPIRE_DB)
    conn.execute(
        """INSERT INTO intake_users
           (id, name, email, password_hash, role, business)
           VALUES (?,?,?,?,?,?)""",
        (user_id, "E2E Founder Test", email, pwd.hash(password), "founder", "workroom"),
    )
    conn.commit()
    conn.close()
    return user_id


def _delete_user(email):
    conn = sqlite3.connect(EMPIRE_DB)
    conn.execute("DELETE FROM intake_users WHERE email = ?", (email,))
    conn.commit()
    conn.close()


def _delete_project(project_id):
    conn = sqlite3.connect(EMPIRE_DB)
    conn.execute("DELETE FROM intake_projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()


# Pool of test artifacts (cleaned up at the end)
_TEST_USERS = []
_TEST_PROJECTS = []


def teardown_module(module):
    for pid in _TEST_PROJECTS:
        try:
            _delete_project(pid)
        except Exception:
            pass
    for email in _TEST_USERS:
        try:
            _delete_user(email)
        except Exception:
            pass


def test_golden_path_anonymous_page_returns_200():
    """Step 1: anonymous page load on the production door.

    Per the founder's CF bypass mandate, an anonymous client can
    reach the intake landing page. We test against the Next.js
    middleware on the local portal (which mirrors the Cloudflare
    ingress path: same middleware, same allowlist)."""
    resp = _http("GET", f"{PORTAL}/intake", headers={"Host": "luxe.empirebox.store"})
    assert resp.status_code == 200, f"Expected 200 on /intake, got {resp.status_code}"


def test_golden_path_command_center_routes_blocked():
    """Step 1b: middleware hard-scope — Command Center routes on the
    luxe host redirect to /intake. This is the safety gate that
    makes the founder's CF bypass safe."""
    for path in ("/dashboard", "/platform", "/max", "/quote", "/workroom"):
        resp = _http("GET", f"{PORTAL}{path}", headers={"Host": "luxe.empirebox.store"}, timeout=5)
        assert resp.status_code in (307, 308), f"Expected {path} to redirect, got {resp.status_code}"


def test_golden_path_quick_signup_lands_in_canonical_db():
    """Step 2: quick signup writes to canonical empire.db with business set."""
    suffix = uuid.uuid4().hex[:10]
    client_email = f"e2e-client-{suffix}@breakmap.local"
    _TEST_USERS.append(client_email)

    resp = _http("POST", f"{BACKEND}/api/v1/intake/signup", data={
        "name": f"E2E Client {suffix}",
        "email": client_email,
        "password": "e2eTestP4ss",
        "role": "client",
        "business": "workroom",
    })
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    payload = resp.json()
    assert "token" in payload, "missing token in response"
    assert payload["user"]["business"] == "workroom", "business not echoed in /signup response"

    # Verify the row is in CANONICAL empire.db (not stale-fork)
    c = sqlite3.connect(EMPIRE_DB)
    row = c.execute("SELECT id, email, role, business FROM intake_users WHERE email = ?", (client_email,)).fetchone()
    c.close()
    assert row is not None, f"user {client_email} not found in {EMPIRE_DB}"
    assert row[3] == "workroom", f"business column empty/wrong: {row[3]}"


def test_golden_path_full_submission_with_image():
    """Step 3+4: full client journey — create a project, upload an image,
    submit, verify the row lands in empire.db with business set."""
    suffix = uuid.uuid4().hex[:10]
    client_email = f"e2e-client-{suffix}@breakmap.local"
    _TEST_USERS.append(client_email)

    signup = _http("POST", f"{BACKEND}/api/v1/intake/signup", data={
        "name": f"E2E Full {suffix}",
        "email": client_email,
        "password": "e2eTestP4ss",
        "role": "client",
        "business": "workroom",
    })
    assert signup.status_code == 200, f"signup failed: {signup.text}"
    token = signup.json()["token"]
    auth = {"Authorization": f"Bearer {token}"}

    # Create project
    proj = _http("POST", f"{BACKEND}/api/v1/intake/projects", headers=auth, data={
        "name": f"E2E Project {suffix}",
        "treatment": "drapery",
        "style": "modern",
        "scope": "single-room",
        "rooms": [{"name": "Living Room", "treatment": "drapery"}],
        "measurements": [{"room": "Living Room", "width": 48, "height": 60}],
        "notes": "E2E golden-path test artifact",
        "business": "workroom",
    })
    assert proj.status_code == 200, f"project create failed: {proj.text}"
    proj_id = proj.json()["id"]
    _TEST_PROJECTS.append(proj_id)

    # Upload a real (small) image
    fake_jpeg = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
        b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e"
        b"\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0"
        b"\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x14\x00\x01"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x00?\x00\x37\xff\xd9"
    )
    upload = _http(
        "POST",
        f"{BACKEND}/api/v1/intake/projects/{proj_id}/photos",
        headers=auth,
        files={"file": ("e2e_probe.jpg", fake_jpeg, "image/jpeg")},
    )
    assert upload.status_code == 200, f"upload failed: {upload.text}"
    uploaded_filename = upload.json()["filename"]

    # Submit
    sub = _http("POST", f"{BACKEND}/api/v1/intake/projects/{proj_id}/submit", headers=auth)
    assert sub.status_code == 200, f"submit failed: {sub.text}"

    # Verify the row in empire.db
    c = sqlite3.connect(EMPIRE_DB)
    row = c.execute(
        "SELECT id, name, status, business, photos FROM intake_projects WHERE id = ?",
        (proj_id,),
    ).fetchone()
    c.close()
    assert row is not None, f"project {proj_id} not found in {EMPIRE_DB}"
    assert row[2] == "submitted", f"status not submitted: {row[2]}"
    assert row[3] == "workroom", f"business not set: {row[3]}"
    photos = json.loads(row[4] or "[]")
    assert any(p["filename"] == uploaded_filename for p in photos), \
        f"uploaded photo {uploaded_filename} not in project.photos"

    # Verify the file landed at CANONICAL path (not stale-fork)
    canonical_path = Path("/home/rg/empire-data/intake_uploads") / proj_id / uploaded_filename
    stale_path = Path("/home/rg/empire-repo/backend/data/intake_uploads") / proj_id / uploaded_filename
    assert canonical_path.exists(), f"file NOT at canonical: {canonical_path}"
    assert not stale_path.exists(), f"file wrongly landed at stale-fork: {stale_path}"


def test_golden_path_founder_admin_sees_project():
    """Step 5: founder's LuxeForge admin surface lists the new project.

    Uses a temp founder admin user (created+cleaned by this module)."""
    suffix = uuid.uuid4().hex[:10]
    admin_email = f"e2e-founder-{suffix}@breakmap.local"
    _TEST_USERS.append(admin_email)
    _create_founder_admin(admin_email, "e2eTestP4ss")

    # Login as founder
    lr = _http("POST", f"{BACKEND}/api/v1/intake/login", data={
        "email": admin_email,
        "password": "e2eTestP4ss",
    })
    assert lr.status_code == 200, f"founder login failed: {lr.text}"
    admin_token = lr.json()["token"]
    auth = {"Authorization": f"Bearer {admin_token}"}

    # Create a project we'll search for
    suffix2 = uuid.uuid4().hex[:10]
    client_email = f"e2e-adminclient-{suffix2}@breakmap.local"
    _TEST_USERS.append(client_email)
    su = _http("POST", f"{BACKEND}/api/v1/intake/signup", data={
        "name": f"E2E AdminClient {suffix2}",
        "email": client_email,
        "password": "e2eTestP4ss",
        "role": "client",
        "business": "workroom",
    })
    assert su.status_code == 200
    ct = su.json()["token"]
    cp = _http("POST", f"{BACKEND}/api/v1/intake/projects", headers={"Authorization": f"Bearer {ct}"}, data={
        "name": f"ADMIN_FIND_ME_{suffix2}",
        "treatment": "drapery",
        "business": "workroom",
    })
    assert cp.status_code == 200
    pid = cp.json()["id"]
    _TEST_PROJECTS.append(pid)

    # Call /admin/projects
    admin_list = _http("GET", f"{BACKEND}/api/v1/intake/admin/projects", headers=auth)
    assert admin_list.status_code == 200, f"admin list failed: {admin_list.text}"
    projs = admin_list.json()
    assert isinstance(projs, list), f"expected list, got {type(projs)}"
    matching = [p for p in projs if p.get("id") == pid]
    assert matching, f"new project {pid} not in admin list ({len(projs)} projects listed)"
    assert matching[0]["business"] == "workroom", \
        f"admin list missing business: {matching[0]}"
