import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.routers import intake_auth


client = TestClient(app)


def _configure_temp_intake(monkeypatch, tmp_path):
    intake_db = tmp_path / "intake.db"
    uploads_dir = tmp_path / "intake_uploads"
    photos_dir = tmp_path / "photos"
    uploads_dir.mkdir()
    photos_dir.mkdir()
    monkeypatch.setattr(intake_auth, "DB_PATH", str(intake_db))
    monkeypatch.setattr(intake_auth, "UPLOADS_DIR", str(uploads_dir))
    monkeypatch.setattr(intake_auth, "PHOTOS_DIR", str(photos_dir))
    intake_auth.init_db()
    return intake_db


def _seed_intake_user(role: str = "client") -> tuple[str, str]:
    user_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    conn = intake_auth.get_db()
    conn.execute(
        """INSERT INTO intake_users
           (id, name, email, phone, password_hash, company, role)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            f"Secret {role.title()}",
            f"{role}-{uuid.uuid4().hex[:8]}@example.com",
            "555-0100",
            "hash",
            "Secret Studio",
            role,
        ),
    )
    conn.execute(
        """INSERT INTO intake_projects
           (id, user_id, intake_code, name, status, rooms, photos, scans, measurements)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            project_id,
            user_id,
            f"INT-TEST-{uuid.uuid4().hex[:6]}",
            "Secret Drapery Project",
            "submitted",
            "[]",
            "[]",
            "[]",
            "[]",
        ),
    )
    conn.commit()
    conn.close()
    return user_id, project_id


def _auth_header_for(user_id: str, email: str = "admin@example.com") -> dict[str, str]:
    return {"Authorization": f"Bearer {intake_auth.create_token(user_id, email)}"}


def test_intake_admin_routes_deny_unauthenticated(monkeypatch, tmp_path):
    _configure_temp_intake(monkeypatch, tmp_path)
    _user_id, project_id = _seed_intake_user()

    checks = [
        ("GET", "/api/v1/intake/admin/projects", None),
        ("GET", "/api/v1/intake/admin/users", None),
        ("GET", "/api/v1/intake/admin/archived", None),
        ("GET", "/api/v1/intake/admin/projects-with-photos", None),
        ("GET", f"/api/v1/intake/admin/projects/{project_id}", None),
        ("PUT", f"/api/v1/intake/admin/users/{_user_id}", {"name": "Changed"}),
        ("DELETE", f"/api/v1/intake/admin/users/{_user_id}", None),
        ("POST", f"/api/v1/intake/admin/users/{_user_id}/restore", None),
        ("POST", f"/api/v1/intake/admin/projects/{project_id}/restore", None),
        ("POST", f"/api/v1/intake/admin/projects/{project_id}/to-quote", {"business_unit": "workroom"}),
    ]

    for method, path, payload in checks:
        response = client.request(method, path, json=payload)
        assert response.status_code == 401, f"{method} {path} leaked without auth"
        body = response.text
        assert "Secret Drapery Project" not in body
        assert "Secret Studio" not in body
        assert "Secret Client" not in body


def test_intake_admin_routes_deny_non_admin_token(monkeypatch, tmp_path):
    _configure_temp_intake(monkeypatch, tmp_path)
    user_id, _project_id = _seed_intake_user(role="client")

    response = client.get("/api/v1/intake/admin/projects", headers=_auth_header_for(user_id, "client@example.com"))

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_public_signup_cannot_create_admin_role(monkeypatch, tmp_path):
    _configure_temp_intake(monkeypatch, tmp_path)

    response = client.post(
        "/api/v1/intake/signup",
        json={
            "name": "Bad Role",
            "email": f"bad-role-{uuid.uuid4().hex[:8]}@example.com",
            "password": "secret123",
            "role": "admin",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid intake role"


def test_public_intake_signup_and_login_still_work(monkeypatch, tmp_path):
    _configure_temp_intake(monkeypatch, tmp_path)
    email = f"designer-{uuid.uuid4().hex[:8]}@example.com"

    signup = client.post(
        "/api/v1/intake/signup",
        json={
            "name": "Design Client",
            "email": email,
            "phone": "555-0111",
            "password": "secret123",
            "company": "Design Studio",
            "role": "designer",
        },
    )
    assert signup.status_code == 200
    assert signup.json()["user"]["role"] == "designer"

    login = client.post(
        "/api/v1/intake/login",
        json={"email": email, "password": "secret123"},
    )
    assert login.status_code == 200
    assert login.json()["token"]


def test_intake_admin_role_can_access_admin_projects(monkeypatch, tmp_path):
    _configure_temp_intake(monkeypatch, tmp_path)
    admin_id, _project_id = _seed_intake_user(role="admin")

    response = client.get("/api/v1/intake/admin/projects", headers=_auth_header_for(admin_id, "admin@example.com"))

    assert response.status_code == 200
    assert isinstance(response.json(), list)
