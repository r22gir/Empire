"""
LuxeForge FREE — Public Intake Portal Auth & Projects.
Designers/clients create accounts, submit projects, upload photos.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError
import sqlite3
import json
import uuid
import os
import shutil
import logging

from app.middleware.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["intake"])

# ── Config ────────────────────────────────────────────────────
JWT_SECRET = os.getenv("INTAKE_JWT_SECRET", "empire-intake-secret-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 72

DB_PATH = os.path.expanduser("~/empire-repo/backend/data/intake.db")
UPLOADS_DIR = os.path.expanduser("~/empire-repo/backend/data/intake_uploads")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


# ── Database init ─────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS intake_users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            password_hash TEXT NOT NULL,
            company TEXT,
            role TEXT DEFAULT 'client',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS intake_projects (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            intake_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            address TEXT,
            status TEXT DEFAULT 'draft',
            rooms TEXT DEFAULT '[]',
            photos TEXT DEFAULT '[]',
            scans TEXT DEFAULT '[]',
            measurements TEXT DEFAULT '[]',
            treatment TEXT,
            style TEXT,
            scope TEXT,
            notes TEXT,
            quote_pdf TEXT,
            selected_proposal TEXT,
            messages TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES intake_users(id)
        );
        CREATE INDEX IF NOT EXISTS idx_projects_user ON intake_projects(user_id);
        CREATE INDEX IF NOT EXISTS idx_projects_code ON intake_projects(intake_code);
    """)
    conn.commit()
    conn.close()


init_db()


# ── JWT helpers ───────────────────────────────────────────────
def create_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(credentials.credentials)
    conn = get_db()
    user = conn.execute("SELECT * FROM intake_users WHERE id = ?", (payload["sub"],)).fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(user)


def _next_intake_code() -> str:
    conn = get_db()
    row = conn.execute("SELECT COUNT(*) as c FROM intake_projects").fetchone()
    conn.close()
    num = (row["c"] or 0) + 1
    return f"INT-{datetime.now().strftime('%Y')}-{num:04d}"


# ── Schemas ───────────────────────────────────────────────────
class SignupRequest(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    password: str
    company: Optional[str] = None
    role: str = "client"  # designer, installer, client


class LoginRequest(BaseModel):
    email: str
    password: str


class ProjectCreate(BaseModel):
    name: str
    address: Optional[str] = None
    treatment: Optional[str] = None
    style: Optional[str] = None
    scope: Optional[str] = None
    rooms: list = Field(default_factory=list)
    measurements: list = Field(default_factory=list)
    notes: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    status: Optional[str] = None
    treatment: Optional[str] = None
    style: Optional[str] = None
    scope: Optional[str] = None
    rooms: Optional[list] = None
    measurements: Optional[list] = None
    notes: Optional[str] = None
    selected_proposal: Optional[str] = None


class MessageCreate(BaseModel):
    content: str


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    password: Optional[str] = None


class AdminUserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  AUTH ENDPOINTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@limiter.limit("10/minute")
@router.post("/signup")
async def signup(request: Request, req: SignupRequest):
    conn = get_db()
    existing = conn.execute("SELECT id FROM intake_users WHERE email = ?", (req.email.lower().strip(),)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = str(uuid.uuid4())
    password_hash = pwd_context.hash(req.password)
    conn.execute(
        "INSERT INTO intake_users (id, name, email, phone, password_hash, company, role) VALUES (?,?,?,?,?,?,?)",
        (user_id, req.name.strip(), req.email.lower().strip(), req.phone, password_hash, req.company, req.role),
    )
    conn.commit()
    conn.close()

    token = create_token(user_id, req.email.lower().strip())
    return {"token": token, "user": {"id": user_id, "name": req.name, "email": req.email, "role": req.role}}


@limiter.limit("10/minute")
@router.post("/login")
async def login(request: Request, req: LoginRequest):
    conn = get_db()
    user = conn.execute("SELECT * FROM intake_users WHERE email = ?", (req.email.lower().strip(),)).fetchone()
    conn.close()
    if not user or not pwd_context.verify(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(user["id"], user["email"])
    return {
        "token": token,
        "user": {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"], "company": user["company"]},
    }


@limiter.limit("30/minute")
@router.get("/me")
async def get_me(request: Request, user=Depends(get_current_user)):
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "phone": user["phone"],
        "company": user["company"],
        "role": user["role"],
        "created_at": user["created_at"],
    }


@limiter.limit("10/minute")
@router.put("/me")
async def update_profile(request: Request, update: ProfileUpdate, user=Depends(get_current_user)):
    """User self-service profile update."""
    conn = get_db()
    fields = []
    values = []
    data = update.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        fields.append("name = ?")
        values.append(data["name"].strip())
    if "phone" in data:
        fields.append("phone = ?")
        values.append(data["phone"])
    if "company" in data:
        fields.append("company = ?")
        values.append(data["company"])
    if "password" in data and data["password"]:
        fields.append("password_hash = ?")
        values.append(pwd_context.hash(data["password"]))
    if fields:
        values.append(user["id"])
        conn.execute(f"UPDATE intake_users SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
    conn.close()
    return await get_me(request, user)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PROJECT ENDPOINTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@limiter.limit("10/minute")
@router.post("/projects")
async def create_project(request: Request, project: ProjectCreate, user=Depends(get_current_user)):
    project_id = str(uuid.uuid4())
    intake_code = _next_intake_code()
    conn = get_db()
    conn.execute(
        """INSERT INTO intake_projects
           (id, user_id, intake_code, name, address, treatment, style, scope, rooms, measurements, notes)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            project_id, user["id"], intake_code, project.name, project.address,
            project.treatment, project.style, project.scope,
            json.dumps(project.rooms), json.dumps(project.measurements), project.notes,
        ),
    )
    conn.commit()
    conn.close()
    return {"id": project_id, "intake_code": intake_code, "status": "draft"}


@limiter.limit("30/minute")
@router.get("/projects")
async def list_projects(request: Request, user=Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM intake_projects WHERE user_id = ? ORDER BY created_at DESC", (user["id"],)
    ).fetchall()
    conn.close()
    projects = []
    for r in rows:
        d = dict(r)
        d["rooms"] = json.loads(d.get("rooms") or "[]")
        d["photos"] = json.loads(d.get("photos") or "[]")
        d["scans"] = json.loads(d.get("scans") or "[]")
        d["measurements"] = json.loads(d.get("measurements") or "[]")
        d["messages"] = json.loads(d.get("messages") or "[]")
        projects.append(d)
    return {"projects": projects, "total": len(projects)}


@limiter.limit("30/minute")
@router.get("/projects/{project_id}")
async def get_project(request: Request, project_id: str, user=Depends(get_current_user)):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM intake_projects WHERE id = ? AND user_id = ?", (project_id, user["id"])
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    d = dict(row)
    d["rooms"] = json.loads(d.get("rooms") or "[]")
    d["photos"] = json.loads(d.get("photos") or "[]")
    d["scans"] = json.loads(d.get("scans") or "[]")
    d["measurements"] = json.loads(d.get("measurements") or "[]")
    d["messages"] = json.loads(d.get("messages") or "[]")
    return d


@limiter.limit("10/minute")
@router.put("/projects/{project_id}")
async def update_project(request: Request, project_id: str, update: ProjectUpdate, user=Depends(get_current_user)):
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM intake_projects WHERE id = ? AND user_id = ?", (project_id, user["id"])
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Project not found")

    fields = []
    values = []
    for key, val in update.model_dump(exclude_unset=True).items():
        if val is not None:
            if isinstance(val, list):
                fields.append(f"{key} = ?")
                values.append(json.dumps(val))
            else:
                fields.append(f"{key} = ?")
                values.append(val)
    if fields:
        fields.append("updated_at = datetime('now')")
        values.append(project_id)
        values.append(user["id"])
        conn.execute(
            f"UPDATE intake_projects SET {', '.join(fields)} WHERE id = ? AND user_id = ?",
            values,
        )
        conn.commit()
    conn.close()
    return await get_project(request, project_id, user)


@limiter.limit("10/minute")
@router.post("/projects/{project_id}/submit")
async def submit_project(request: Request, project_id: str, user=Depends(get_current_user)):
    conn = get_db()
    conn.execute(
        "UPDATE intake_projects SET status = 'submitted', updated_at = datetime('now') WHERE id = ? AND user_id = ?",
        (project_id, user["id"]),
    )
    # Fetch project data for event trigger
    row = conn.execute("SELECT * FROM intake_projects WHERE id = ?", (project_id,)).fetchone()
    conn.commit()
    conn.close()

    # Fire desk event: new project submitted
    if row:
        try:
            import asyncio
            from app.services.max.desks.desk_scheduler import desk_scheduler
            project_data = {
                "name": row["name"],
                "treatment": row["treatment"],
                "photos": json.loads(row["photos"] or "[]"),
                "measurements": json.loads(row["measurements"] or "[]"),
            }
            asyncio.create_task(desk_scheduler.on_new_intake_project(project_data))
        except Exception as e:
            logger.warning(f"Desk event trigger failed: {e}")

    return {"status": "submitted", "message": "Project submitted! We'll review and send a quote within 24 hours."}


@limiter.limit("10/minute")
@router.post("/projects/{project_id}/message")
async def add_message(request: Request, project_id: str, msg: MessageCreate, user=Depends(get_current_user)):
    conn = get_db()
    row = conn.execute(
        "SELECT messages FROM intake_projects WHERE id = ? AND user_id = ?", (project_id, user["id"])
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Project not found")
    messages = json.loads(row["messages"] or "[]")
    messages.append({
        "id": str(uuid.uuid4()),
        "from": user["name"],
        "role": user["role"],
        "content": msg.content,
        "timestamp": datetime.utcnow().isoformat(),
    })
    conn.execute(
        "UPDATE intake_projects SET messages = ?, updated_at = datetime('now') WHERE id = ?",
        (json.dumps(messages), project_id),
    )
    conn.commit()
    conn.close()
    return {"message": "sent", "total_messages": len(messages)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  FILE UPLOAD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@limiter.limit("10/minute")
@router.post("/projects/{project_id}/photos")
async def upload_photo(
    request: Request,
    project_id: str,
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    conn = get_db()
    row = conn.execute(
        "SELECT photos FROM intake_projects WHERE id = ? AND user_id = ?", (project_id, user["id"])
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Project not found")

    # Save file
    project_dir = os.path.join(UPLOADS_DIR, project_id)
    os.makedirs(project_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "photo.jpg")[1] or ".jpg"
    filename = f"{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(project_dir, filename)
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Update DB
    photos = json.loads(row["photos"] or "[]")
    photos.append({
        "filename": filename,
        "original_name": file.filename,
        "path": f"/intake_uploads/{project_id}/{filename}",
        "uploaded_at": datetime.utcnow().isoformat(),
    })
    conn.execute(
        "UPDATE intake_projects SET photos = ?, updated_at = datetime('now') WHERE id = ?",
        (json.dumps(photos), project_id),
    )
    conn.commit()
    conn.close()

    # Fire desk event: new photo uploaded
    try:
        import asyncio
        from app.services.max.desks.desk_scheduler import desk_scheduler
        asyncio.create_task(desk_scheduler.on_photo_uploaded(
            project_id, {"original_name": file.filename, "path": photos[-1]["path"]}
        ))
    except Exception as e:
        logger.warning(f"Photo event trigger failed: {e}")

    return {"filename": filename, "total_photos": len(photos)}


@limiter.limit("10/minute")
@router.post("/projects/{project_id}/scans")
async def upload_scan(
    request: Request,
    project_id: str,
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    conn = get_db()
    row = conn.execute(
        "SELECT scans FROM intake_projects WHERE id = ? AND user_id = ?", (project_id, user["id"])
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Project not found")

    project_dir = os.path.join(UPLOADS_DIR, project_id)
    os.makedirs(project_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "scan.glb")[1] or ".glb"
    filename = f"scan_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(project_dir, filename)
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    scans = json.loads(row["scans"] or "[]")
    scans.append({
        "filename": filename,
        "original_name": file.filename,
        "path": f"/intake_uploads/{project_id}/{filename}",
        "uploaded_at": datetime.utcnow().isoformat(),
    })
    conn.execute(
        "UPDATE intake_projects SET scans = ?, updated_at = datetime('now') WHERE id = ?",
        (json.dumps(scans), project_id),
    )
    conn.commit()
    conn.close()

    return {"filename": filename, "total_scans": len(scans)}


# ── Admin endpoints (for Command Center) ─────────────────────
@limiter.limit("30/minute")
@router.get("/admin/projects")
async def admin_list_all_projects(request: Request):
    """List all intake projects with user info (for founder dashboard)."""
    conn = get_db()
    rows = conn.execute("""
        SELECT p.*, u.name as user_name, u.email as user_email,
               u.company as user_company, u.role as user_role
        FROM intake_projects p
        LEFT JOIN intake_users u ON p.user_id = u.id
        ORDER BY p.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@limiter.limit("30/minute")
@router.get("/admin/users")
async def admin_list_all_users(request: Request):
    """List all registered intake users (for founder dashboard)."""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, email, phone, company, role, created_at FROM intake_users ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@limiter.limit("30/minute")
@router.get("/admin/projects/{project_id}")
async def admin_get_project(request: Request, project_id: str):
    """Get single project with full details (for founder dashboard)."""
    conn = get_db()
    row = conn.execute("""
        SELECT p.*, u.name as user_name, u.email as user_email,
               u.company as user_company, u.role as user_role
        FROM intake_projects p
        LEFT JOIN intake_users u ON p.user_id = u.id
        WHERE p.id = ?
    """, (project_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return dict(row)


@limiter.limit("10/minute")
@router.put("/admin/users/{user_id}")
async def admin_update_user(request: Request, user_id: str, update: AdminUserUpdate):
    """Admin: update any user's info."""
    conn = get_db()
    row = conn.execute("SELECT id FROM intake_users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    fields = []
    values = []
    data = update.model_dump(exclude_unset=True)
    for key, val in data.items():
        if val is not None:
            fields.append(f"{key} = ?")
            values.append(val)
    if fields:
        values.append(user_id)
        conn.execute(f"UPDATE intake_users SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
    updated = conn.execute("SELECT id, name, email, phone, company, role, created_at FROM intake_users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(updated)


@limiter.limit("10/minute")
@router.delete("/admin/users/{user_id}")
async def admin_delete_user(request: Request, user_id: str):
    """Admin: delete a user and their projects."""
    conn = get_db()
    row = conn.execute("SELECT id FROM intake_users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    conn.execute("DELETE FROM intake_projects WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM intake_users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted", "user_id": user_id}


@limiter.limit("10/minute")
@router.post("/admin/projects/{project_id}/to-quote")
async def convert_to_quote(request: Request, project_id: str):
    """Convert an intake project into an Empire Workroom quote."""
    import importlib
    conn = get_db()
    row = conn.execute("""
        SELECT p.*, u.name as user_name, u.email as user_email,
               u.phone as user_phone, u.company as user_company
        FROM intake_projects p
        LEFT JOIN intake_users u ON p.user_id = u.id
        WHERE p.id = ?
    """, (project_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")

    project = dict(row)
    measurements_raw = json.loads(project.get("measurements") or "[]")
    rooms_raw = json.loads(project.get("rooms") or "[]")
    photos_raw = json.loads(project.get("photos") or "[]")

    # Build rooms list for the quote from measurements + treatment info
    rooms = []
    for m in measurements_raw:
        rooms.append({
            "name": m.get("room", "Window"),
            "windows": [{
                "name": m.get("room", "Window"),
                "width": float(m.get("width", 0)),
                "height": float(m.get("height", 0)),
                "quantity": 1,
                "treatmentType": project.get("treatment", "drapery"),
            }],
        })

    # If rooms_raw has items (multi-item projects), use those too
    for r in rooms_raw:
        if isinstance(r, dict) and r.get("name"):
            rooms.append({
                "name": r.get("name", "Room"),
                "windows": [{
                    "name": r.get("name", "Item"),
                    "width": 0,
                    "height": 0,
                    "quantity": 1,
                    "treatmentType": r.get("treatment", project.get("treatment", "")),
                    "description": r.get("description", ""),
                }],
            })

    # Build quote payload
    quote_data = {
        "customer_name": project.get("user_name") or "Intake Client",
        "customer_email": project.get("user_email") or "",
        "customer_phone": project.get("user_phone") or "",
        "customer_address": project.get("address") or "",
        "project_name": project.get("name") or "Intake Project",
        "project_description": f"From LuxeForge intake {project.get('intake_code', '')}. "
                               f"Treatment: {project.get('treatment', 'N/A')}. "
                               f"Style: {project.get('style', 'N/A')}. "
                               f"Scope: {project.get('scope', 'N/A')}.",
        "notes": project.get("notes") or "",
        "rooms": rooms,
        "line_items": [
            {
                "description": f"{w.get('name', 'Window')} — {w.get('treatmentType', 'drapery')}",
                "quantity": w.get("quantity", 1),
                "unit": "ea",
                "rate": 0.0,
                "amount": 0.0,
                "category": "labor",
            }
            for room in rooms
            for w in room.get("windows", [])
        ],
        "valid_days": 30,
    }

    # Create the quote via the quotes router
    try:
        quotes_mod = importlib.import_module("app.routers.quotes")
        payload = quotes_mod.QuoteCreate(**quote_data)
        result = await quotes_mod.create_quote(payload)

        # Attach photos and intake_project_id to the quote JSON file
        quote_obj = result.get("quote", {})
        quote_id = quote_obj.get("id")
        if quote_id:
            quote_photos = []
            for p in photos_raw:
                quote_photos.append({
                    "filename": p.get("filename", ""),
                    "url": f"/intake_uploads/{project_id}/{p.get('filename', '')}",
                    "original_name": p.get("original_name", p.get("filename", "")),
                    "uploaded_at": p.get("uploaded_at", ""),
                })
            quote_obj["intake_project_id"] = project_id
            quote_obj["photos"] = quote_photos
            quotes_mod._save_quote(quote_obj)

        # Update intake project status
        conn2 = get_db()
        conn2.execute(
            "UPDATE intake_projects SET status = 'quote-ready', updated_at = datetime('now') WHERE id = ?",
            (project_id,),
        )
        conn2.commit()
        conn2.close()

        return {
            "status": "created",
            "quote_id": result.get("quote", {}).get("id"),
            "quote_number": result.get("quote", {}).get("quote_number"),
            "intake_code": project.get("intake_code"),
        }
    except Exception as e:
        logger.error(f"Failed to convert intake to quote: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@limiter.limit("30/minute")
@router.get("/admin/projects-with-photos")
async def admin_projects_with_photos(request: Request):
    """Return intake projects that have photos, for the QuoteBuilder to list."""
    conn = get_db()
    rows = conn.execute("""
        SELECT p.id, p.name, p.intake_code, p.status, p.photos, p.created_at,
               u.name as customer_name
        FROM intake_projects p
        LEFT JOIN intake_users u ON p.user_id = u.id
        WHERE p.photos IS NOT NULL AND p.photos != '[]' AND p.photos != ''
        ORDER BY p.created_at DESC
    """).fetchall()
    conn.close()

    results = []
    for row in rows:
        project = dict(row)
        photos_raw = json.loads(project.get("photos") or "[]")
        if not photos_raw:
            continue
        photos_out = []
        for p in photos_raw:
            photos_out.append({
                "url": f"/intake_uploads/{project['id']}/{p.get('filename', '')}",
                "filename": p.get("filename", ""),
                "original_name": p.get("original_name", p.get("filename", "")),
            })
        results.append({
            "id": project["id"],
            "name": project.get("name"),
            "intake_code": project.get("intake_code"),
            "status": project.get("status"),
            "customer_name": project.get("customer_name"),
            "photo_count": len(photos_out),
            "photos": photos_out,
            "created_at": project.get("created_at"),
        })

    return {"projects": results, "count": len(results)}
