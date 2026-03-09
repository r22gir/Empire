"""
AMP — Actitud Mental Positiva. Personal development platform.
User accounts, mood tracking, journal, affirmations, course progress.
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError
import sqlite3, json, uuid, os, logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["amp"])

JWT_SECRET = os.getenv("AMP_JWT_SECRET", "empire-amp-secret-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 72

DB_PATH = os.path.expanduser("~/empire-repo/backend/data/amp.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS amp_users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            language TEXT DEFAULT 'es',
            streak INTEGER DEFAULT 0,
            last_visit TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS amp_moods (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            mood TEXT NOT NULL,
            emoji TEXT,
            note TEXT,
            date TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES amp_users(id)
        );
        CREATE TABLE IF NOT EXISTS amp_journal (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            content TEXT NOT NULL,
            gratitude TEXT,
            date TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES amp_users(id)
        );
        CREATE TABLE IF NOT EXISTS amp_progress (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            course_id TEXT NOT NULL,
            lesson_id TEXT NOT NULL,
            completed_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES amp_users(id)
        );
        CREATE INDEX IF NOT EXISTS idx_moods_user ON amp_moods(user_id);
        CREATE INDEX IF NOT EXISTS idx_journal_user ON amp_journal(user_id);
        CREATE INDEX IF NOT EXISTS idx_progress_user ON amp_progress(user_id);
    """)
    conn.commit()
    conn.close()


init_db()


# ── JWT ──
def create_token(user_id: str, email: str) -> str:
    return jwt.encode(
        {"sub": user_id, "email": email, "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)},
        JWT_SECRET, algorithm=JWT_ALGORITHM,
    )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(401, "Invalid token")
    conn = get_db()
    user = conn.execute("SELECT * FROM amp_users WHERE id = ?", (payload["sub"],)).fetchone()
    conn.close()
    if not user:
        raise HTTPException(401, "User not found")
    return dict(user)


# ── Schemas ──
class SignupReq(BaseModel):
    name: str
    email: str
    password: str

class LoginReq(BaseModel):
    email: str
    password: str

class MoodReq(BaseModel):
    mood: str
    emoji: Optional[str] = None
    note: Optional[str] = None
    date: Optional[str] = None

class JournalReq(BaseModel):
    content: str
    gratitude: Optional[str] = None
    date: Optional[str] = None

class ProgressReq(BaseModel):
    course_id: str
    lesson_id: str

class ProfileReq(BaseModel):
    name: Optional[str] = None
    language: Optional[str] = None
    password: Optional[str] = None


# ━━━ AUTH ━━━
@router.post("/signup")
async def signup(req: SignupReq):
    conn = get_db()
    if conn.execute("SELECT id FROM amp_users WHERE email = ?", (req.email.lower().strip(),)).fetchone():
        conn.close()
        raise HTTPException(400, "Email already registered")
    uid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO amp_users (id, name, email, password_hash) VALUES (?,?,?,?)",
        (uid, req.name.strip(), req.email.lower().strip(), pwd_context.hash(req.password)),
    )
    conn.commit()
    conn.close()
    return {"token": create_token(uid, req.email), "user": {"id": uid, "name": req.name, "email": req.email}}


@router.post("/login")
async def login(req: LoginReq):
    conn = get_db()
    user = conn.execute("SELECT * FROM amp_users WHERE email = ?", (req.email.lower().strip(),)).fetchone()
    conn.close()
    if not user or not pwd_context.verify(req.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    return {"token": create_token(user["id"], user["email"]), "user": {"id": user["id"], "name": user["name"], "email": user["email"]}}


@router.get("/me")
async def get_me(user=Depends(get_current_user)):
    conn = get_db()
    mood_count = conn.execute("SELECT COUNT(*) as c FROM amp_moods WHERE user_id = ?", (user["id"],)).fetchone()["c"]
    journal_count = conn.execute("SELECT COUNT(*) as c FROM amp_journal WHERE user_id = ?", (user["id"],)).fetchone()["c"]
    lessons_done = conn.execute("SELECT COUNT(*) as c FROM amp_progress WHERE user_id = ?", (user["id"],)).fetchone()["c"]
    conn.close()
    return {
        "id": user["id"], "name": user["name"], "email": user["email"],
        "language": user["language"], "streak": user["streak"],
        "last_visit": user["last_visit"], "created_at": user["created_at"],
        "stats": {"moods": mood_count, "journals": journal_count, "lessons_completed": lessons_done},
    }


@router.put("/me")
async def update_profile(req: ProfileReq, user=Depends(get_current_user)):
    conn = get_db()
    fields, values = [], []
    if req.name:
        fields.append("name = ?"); values.append(req.name.strip())
    if req.language:
        fields.append("language = ?"); values.append(req.language)
    if req.password:
        fields.append("password_hash = ?"); values.append(pwd_context.hash(req.password))
    if fields:
        values.append(user["id"])
        conn.execute(f"UPDATE amp_users SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
    conn.close()
    return await get_me(user)


# ━━━ MOOD ━━━
@router.post("/moods")
async def log_mood(req: MoodReq, user=Depends(get_current_user)):
    date = req.date or datetime.utcnow().strftime("%Y-%m-%d")
    conn = get_db()
    existing = conn.execute("SELECT id FROM amp_moods WHERE user_id = ? AND date = ?", (user["id"], date)).fetchone()
    if existing:
        conn.execute("UPDATE amp_moods SET mood=?, emoji=?, note=? WHERE id=?", (req.mood, req.emoji, req.note, existing["id"]))
    else:
        conn.execute("INSERT INTO amp_moods (id, user_id, mood, emoji, note, date) VALUES (?,?,?,?,?,?)",
                     (str(uuid.uuid4()), user["id"], req.mood, req.emoji, req.note, date))
    # Update streak
    conn.execute("UPDATE amp_users SET last_visit = ?, streak = streak + 1 WHERE id = ?", (date, user["id"]))
    conn.commit()
    conn.close()
    return {"status": "ok", "date": date}


@router.get("/moods")
async def get_moods(user=Depends(get_current_user), month: Optional[str] = None):
    conn = get_db()
    if month:
        rows = conn.execute("SELECT * FROM amp_moods WHERE user_id = ? AND date LIKE ? ORDER BY date DESC",
                            (user["id"], f"{month}%")).fetchall()
    else:
        rows = conn.execute("SELECT * FROM amp_moods WHERE user_id = ? ORDER BY date DESC LIMIT 90",
                            (user["id"],)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ━━━ JOURNAL ━━━
@router.post("/journal")
async def write_journal(req: JournalReq, user=Depends(get_current_user)):
    date = req.date or datetime.utcnow().strftime("%Y-%m-%d")
    conn = get_db()
    conn.execute("INSERT INTO amp_journal (id, user_id, content, gratitude, date) VALUES (?,?,?,?,?)",
                 (str(uuid.uuid4()), user["id"], req.content, req.gratitude, date))
    conn.commit()
    conn.close()
    return {"status": "ok", "date": date}


@router.get("/journal")
async def get_journal(user=Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute("SELECT * FROM amp_journal WHERE user_id = ? ORDER BY date DESC LIMIT 30",
                        (user["id"],)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ━━━ COURSE PROGRESS ━━━
@router.post("/progress")
async def mark_lesson(req: ProgressReq, user=Depends(get_current_user)):
    conn = get_db()
    existing = conn.execute("SELECT id FROM amp_progress WHERE user_id = ? AND course_id = ? AND lesson_id = ?",
                            (user["id"], req.course_id, req.lesson_id)).fetchone()
    if not existing:
        conn.execute("INSERT INTO amp_progress (id, user_id, course_id, lesson_id) VALUES (?,?,?,?)",
                     (str(uuid.uuid4()), user["id"], req.course_id, req.lesson_id))
        conn.commit()
    conn.close()
    return {"status": "ok"}


@router.get("/progress")
async def get_progress(user=Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute("SELECT * FROM amp_progress WHERE user_id = ? ORDER BY completed_at DESC",
                        (user["id"],)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ━━━ ADMIN (for Command Center) ━━━
@router.get("/admin/users")
async def admin_users():
    conn = get_db()
    rows = conn.execute("SELECT id, name, email, language, streak, last_visit, created_at FROM amp_users ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/admin/stats")
async def admin_stats():
    conn = get_db()
    users = conn.execute("SELECT COUNT(*) as c FROM amp_users").fetchone()["c"]
    moods = conn.execute("SELECT COUNT(*) as c FROM amp_moods").fetchone()["c"]
    journals = conn.execute("SELECT COUNT(*) as c FROM amp_journal").fetchone()["c"]
    conn.close()
    return {"total_users": users, "total_moods": moods, "total_journals": journals}
