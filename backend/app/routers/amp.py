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
        CREATE TABLE IF NOT EXISTS amp_content (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            content_text TEXT,
            audio_url TEXT,
            duration_seconds INTEGER DEFAULT 0,
            pillar TEXT,
            mood_tags TEXT,
            category TEXT,
            author TEXT,
            premium INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS amp_courses (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            pillar TEXT,
            duration_days INTEGER,
            lesson_count INTEGER,
            image_url TEXT,
            premium INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS amp_lessons (
            id TEXT PRIMARY KEY,
            course_id TEXT NOT NULL,
            day_number INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            content_text TEXT,
            audio_url TEXT,
            duration_seconds INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (course_id) REFERENCES amp_courses(id)
        );
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


# ━━━ CONTENT LIBRARY ━━━
@router.get("/content")
async def list_content(type: Optional[str] = None, pillar: Optional[str] = None,
                       mood: Optional[str] = None, premium: Optional[int] = None,
                       limit: int = 50):
    """List content items with optional filters."""
    conn = get_db()
    query = "SELECT * FROM amp_content WHERE 1=1"
    params = []
    if type:
        query += " AND type = ?"; params.append(type)
    if pillar:
        query += " AND pillar = ?"; params.append(pillar)
    if mood:
        query += " AND mood_tags LIKE ?"; params.append(f'%"{mood}"%')
    if premium is not None:
        query += " AND premium = ?"; params.append(premium)
    query += " ORDER BY sort_order, created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/content/{content_id}")
async def get_content(content_id: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM amp_content WHERE id = ?", (content_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Content not found")
    return dict(row)


@router.get("/recommend")
async def recommend_content(mood: str, limit: int = 5):
    """Get content recommendations based on current mood."""
    MOOD_MAP = {
        "happy": {"pillars": ["liderazgo", "mentalidad"], "categories": ["gratitude", "leadership", "abundance"]},
        "peaceful": {"pillars": ["bienestar"], "categories": ["meditation", "mindfulness", "sleep"]},
        "neutral": {"pillars": ["mentalidad", "liderazgo"], "categories": ["focus", "productivity", "growth"]},
        "sad": {"pillars": ["bienestar", "mentalidad"], "categories": ["self-love", "healing", "gratitude"]},
        "frustrated": {"pillars": ["bienestar", "liderazgo"], "categories": ["stress", "breathing", "patience"]},
        "anxious": {"pillars": ["bienestar"], "categories": ["anxiety", "breathing", "grounding", "calm"]},
        "grateful": {"pillars": ["mentalidad"], "categories": ["gratitude", "abundance", "joy"]},
        "motivated": {"pillars": ["liderazgo", "mentalidad"], "categories": ["leadership", "goals", "abundance"]},
    }
    mapping = MOOD_MAP.get(mood.lower(), {"pillars": ["bienestar"], "categories": ["meditation"]})

    conn = get_db()
    results = []

    # First try mood_tags match
    tagged = conn.execute(
        "SELECT * FROM amp_content WHERE mood_tags LIKE ? ORDER BY RANDOM() LIMIT ?",
        (f'%"{mood}"%', limit)
    ).fetchall()
    results.extend([dict(r) for r in tagged])

    # Then fill with pillar/category matches
    if len(results) < limit:
        pillar_placeholders = ",".join(["?"] * len(mapping["pillars"]))
        exclude_ids = [r["id"] for r in results]
        if exclude_ids:
            exclude_placeholders = ",".join(["?"] * len(exclude_ids))
            more = conn.execute(
                f"SELECT * FROM amp_content WHERE pillar IN ({pillar_placeholders}) AND id NOT IN ({exclude_placeholders}) ORDER BY RANDOM() LIMIT ?",
                [*mapping["pillars"], *exclude_ids, limit - len(results)]
            ).fetchall()
        else:
            more = conn.execute(
                f"SELECT * FROM amp_content WHERE pillar IN ({pillar_placeholders}) ORDER BY RANDOM() LIMIT ?",
                [*mapping["pillars"], limit - len(results)]
            ).fetchall()
        results.extend([dict(r) for r in more])

    conn.close()
    return {"mood": mood, "recommendations": results}


# ━━━ COURSES ━━━
@router.get("/courses")
async def list_courses():
    conn = get_db()
    rows = conn.execute("SELECT * FROM amp_courses ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/courses/{course_id}")
async def get_course(course_id: str):
    conn = get_db()
    course = conn.execute("SELECT * FROM amp_courses WHERE id = ?", (course_id,)).fetchone()
    if not course:
        conn.close()
        raise HTTPException(404, "Course not found")
    lessons = conn.execute("SELECT * FROM amp_lessons WHERE course_id = ? ORDER BY day_number", (course_id,)).fetchall()
    conn.close()
    result = dict(course)
    result["lessons"] = [dict(l) for l in lessons]
    return result


@router.get("/courses/{course_id}/lessons")
async def get_course_lessons(course_id: str):
    conn = get_db()
    rows = conn.execute("SELECT * FROM amp_lessons WHERE course_id = ? ORDER BY day_number", (course_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ━━━ SEED (admin) ━━━
@router.post("/admin/seed")
async def seed_content():
    """Seed the content database with initial AMP content."""
    conn = get_db()

    # Check if already seeded
    count = conn.execute("SELECT COUNT(*) as c FROM amp_content").fetchone()["c"]
    if count > 0:
        conn.close()
        return {"status": "already_seeded", "content_count": count}

    # ── AFFIRMATIONS (50) ──
    affirmations = [
        # Mentalidad
        ("Hoy elijo la alegría. Mi mente es fuerte y mi corazón está abierto.", "mentalidad", '["happy","grateful"]', "joy"),
        ("Soy capaz de superar cualquier desafío que la vida me presente.", "mentalidad", '["frustrated","motivated"]', "resilience"),
        ("Mi actitud positiva es mi superpoder más grande.", "mentalidad", '["motivated","happy"]', "mindset"),
        ("Cada día es una nueva oportunidad para crecer y brillar.", "mentalidad", '["neutral","motivated"]', "growth"),
        ("Mi mente positiva crea mi realidad positiva.", "mentalidad", '["neutral","motivated"]', "mindset"),
        ("Tengo el poder de transformar mis pensamientos y mi vida.", "mentalidad", '["frustrated","sad"]', "transformation"),
        ("Hoy me comprometo con mi crecimiento personal.", "mentalidad", '["motivated","neutral"]', "growth"),
        ("La alegría no es un destino, es el camino que elijo cada día.", "mentalidad", '["happy","grateful"]', "joy"),
        ("Abrazo cada momento con gratitud y esperanza.", "mentalidad", '["grateful","peaceful"]', "gratitude"),
        ("Confío en mi proceso de aprendizaje y sanación.", "mentalidad", '["sad","anxious"]', "healing"),
        ("Mis pensamientos son semillas. Hoy planto las mejores.", "mentalidad", '["neutral","motivated"]', "mindset"),
        ("La adversidad me fortalece. Cada reto es un maestro.", "mentalidad", '["frustrated","sad"]', "resilience"),
        ("Hoy suelto lo que no puedo controlar y abrazo lo que sí.", "mentalidad", '["anxious","frustrated"]', "acceptance"),
        ("Mi potencial es ilimitado cuando mi mente está en paz.", "mentalidad", '["peaceful","motivated"]', "potential"),
        ("Elijo ver lo bueno en cada situación, por difícil que sea.", "mentalidad", '["sad","frustrated"]', "optimism"),
        # Bienestar
        ("Mi bienestar es mi prioridad. Merezco paz, amor y abundancia.", "bienestar", '["peaceful","grateful"]', "self-love"),
        ("La paz interior es mi derecho. Hoy la reclamo con amor.", "bienestar", '["anxious","sad"]', "peace"),
        ("Hoy planto semillas de alegría que florecerán mañana.", "bienestar", '["happy","grateful"]', "joy"),
        ("Mi cuerpo es mi templo. Lo cuido con amor y gratitud.", "bienestar", '["neutral","peaceful"]', "wellness"),
        ("Respiro profundo. Estoy aquí. Estoy bien. Todo fluye.", "bienestar", '["anxious","frustrated"]', "calm"),
        ("Mi descanso es sagrado. Me permito parar y recargar.", "bienestar", '["sad","anxious"]', "rest"),
        ("Cada respiración me conecta con la calma que llevo dentro.", "bienestar", '["anxious","neutral"]', "breathing"),
        ("Hoy elijo la calma sobre el caos. La paz sobre la prisa.", "bienestar", '["frustrated","anxious"]', "calm"),
        ("Mi energía es valiosa. La invierto en lo que me nutre.", "bienestar", '["neutral","motivated"]', "energy"),
        ("Merezco momentos de silencio y conexión conmigo mismo/a.", "bienestar", '["sad","peaceful"]', "mindfulness"),
        # Liderazgo
        ("Soy el líder de mi propia vida y elijo caminar con propósito.", "liderazgo", '["motivated","happy"]', "leadership"),
        ("La gratitud transforma mi perspectiva y abre puertas increíbles.", "liderazgo", '["grateful","motivated"]', "gratitude"),
        ("Lidero con el ejemplo. Mis acciones inspiran a otros.", "liderazgo", '["motivated","happy"]', "leadership"),
        ("La verdadera fortaleza está en ser vulnerable y auténtico.", "liderazgo", '["sad","neutral"]', "authenticity"),
        ("Hoy sirvo a los demás desde mi mejor versión.", "liderazgo", '["grateful","motivated"]', "service"),
        ("Mi integridad es mi brújula. Nunca pierdo el norte.", "liderazgo", '["neutral","motivated"]', "integrity"),
        ("Cada persona que encuentro tiene algo que enseñarme.", "liderazgo", '["neutral","peaceful"]', "humility"),
        ("Mi voz importa. Hoy la uso con sabiduría y amor.", "liderazgo", '["motivated","frustrated"]', "communication"),
        ("Construyo puentes, no muros. La conexión es mi fortaleza.", "liderazgo", '["peaceful","grateful"]', "connection"),
        ("El cambio empieza en mí. Soy el líder que el mundo necesita.", "liderazgo", '["motivated","happy"]', "change"),
        # More mixed
        ("La vida me regala exactamente lo que necesito para crecer.", "mentalidad", '["neutral","grateful"]', "trust"),
        ("Soy digno/a de amor, éxito y todas las cosas buenas.", "bienestar", '["sad","anxious"]', "self-worth"),
        ("Hoy celebro mis pequeños logros. Cada paso cuenta.", "mentalidad", '["happy","grateful"]', "celebration"),
        ("Mi corazón está lleno de compasión, empezando por mí mismo/a.", "bienestar", '["sad","peaceful"]', "compassion"),
        ("La creatividad fluye a través de mí cuando estoy en paz.", "mentalidad", '["peaceful","motivated"]', "creativity"),
        ("Mis errores no me definen. Mi resiliencia sí.", "mentalidad", '["frustrated","sad"]', "resilience"),
        ("Hoy soy más fuerte que ayer y más sabio/a que mañana.", "liderazgo", '["motivated","neutral"]', "growth"),
        ("La abundancia está en todas partes. Abro mis ojos para verla.", "mentalidad", '["grateful","happy"]', "abundance"),
        ("Mi sonrisa es un regalo que comparto con el mundo.", "bienestar", '["happy","peaceful"]', "joy"),
        ("Confío en el universo. Todo llega en el momento perfecto.", "bienestar", '["anxious","neutral"]', "trust"),
        ("Hoy dejo ir el miedo y abrazo la fe en mí mismo/a.", "mentalidad", '["anxious","frustrated"]', "courage"),
        ("Mi historia tiene poder. Compartirla puede sanar a otros.", "liderazgo", '["grateful","motivated"]', "sharing"),
        ("La disciplina es el puente entre mis metas y mis logros.", "liderazgo", '["motivated","neutral"]', "discipline"),
        ("Hoy honro mi cuerpo, mi mente y mi espíritu con amor.", "bienestar", '["peaceful","grateful"]', "wholeness"),
        ("El éxito no es un destino. Es la persona en quien me convierto.", "liderazgo", '["motivated","happy"]', "success"),
    ]

    for i, (text, pillar, moods, cat) in enumerate(affirmations):
        conn.execute(
            "INSERT INTO amp_content (id, type, title, description, content_text, pillar, mood_tags, category, author, sort_order) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (f"aff-{i+1:03d}", "affirmation", text[:60] + "..." if len(text) > 60 else text,
             "Afirmación diaria", text, pillar, moods, cat, "AMP Team", i)
        )

    # ── MEDITATIONS (30) ──
    meditations = [
        ("Respiración de la Mañana", "Comienza tu día con una respiración consciente que llena tu cuerpo de energía y paz. Inhala durante 4 segundos, sostén 4, exhala 6. Repite este ciclo mientras visualizas luz dorada entrando en tu cuerpo.", 300, "bienestar", '["neutral","anxious"]', "breathing", False),
        ("Meditación de Gratitud", "Cultiva un corazón agradecido. Piensa en 3 cosas por las que estás agradecido/a hoy. Siente la gratitud en tu pecho. Deja que esa calidez se expanda por todo tu ser.", 600, "mentalidad", '["grateful","happy"]', "gratitude", False),
        ("Visualización del Líder Interior", "Conecta con tu poder interior. Imagina a tu yo más fuerte y sabio. ¿Qué consejos te daría? ¿Cómo se mueve por el mundo? Visualiza que te conviertes en esa persona.", 720, "liderazgo", '["motivated","neutral"]', "leadership", False),
        ("Calma para la Ansiedad", "Técnica 5-4-3-2-1: nombra 5 cosas que ves, 4 que tocas, 3 que escuchas, 2 que hueles, 1 que saboreas. Esta técnica de grounding te ancla al presente.", 480, "bienestar", '["anxious","frustrated"]', "anxiety", False),
        ("Afirmaciones de Abundancia", "Reprograma tu mente con afirmaciones de prosperidad. Repite en silencio: 'La abundancia fluye hacia mí. Merezco éxito y prosperidad. El universo conspira a mi favor.'", 420, "mentalidad", '["motivated","neutral"]', "abundance", False),
        ("Relajación para Dormir", "Un viaje guiado hacia un sueño profundo. Relaja cada parte de tu cuerpo, empezando por los pies. Imagina que flotas en un mar tibio bajo las estrellas.", 900, "bienestar", '["sad","anxious","peaceful"]', "sleep", False),
        ("Body Scan de Bienestar", "Recorre tu cuerpo de pies a cabeza. En cada zona, envía amor y gratitud. Suelta la tensión que encuentres. Tu cuerpo es tu hogar — trátalo con amor.", 600, "bienestar", '["neutral","sad"]', "wellness", False),
        ("Meditación del Perdón", "Libera el peso del resentimiento. Visualiza a quien necesitas perdonar. Envíale luz. Repite: 'Te libero y me libero.' El perdón es un regalo que te das a ti mismo/a.", 720, "mentalidad", '["frustrated","sad"]', "healing", False),
        ("Energía Matutina", "Despierta tu cuerpo y mente con esta meditación activa. Estira, respira profundo, y establece tu intención para el día. Hoy será un gran día.", 420, "bienestar", '["neutral","motivated"]', "energy", False),
        ("Mindfulness en lo Cotidiano", "Aprende a estar presente en las actividades diarias. Come con atención. Camina con consciencia. Escucha con el corazón. La vida sucede ahora.", 600, "bienestar", '["neutral","peaceful"]', "mindfulness", False),
        ("Sanación del Niño Interior", "Conecta con tu yo más joven. Abrázalo con amor. Dile que está seguro, que es amado, que todo va a estar bien. La sanación empieza con esta conversación.", 900, "bienestar", '["sad","anxious"]', "healing", True),
        ("Meditación del Propósito", "¿Para qué estás aquí? Explora tu misión de vida a través de la meditación. Escucha tu voz interior. Tu propósito ya vive dentro de ti.", 720, "liderazgo", '["neutral","motivated"]', "purpose", True),
        ("Liberación del Estrés", "Técnica de tensión progresiva: tensa cada grupo muscular por 5 segundos, luego suelta. Siente cómo la tensión sale de tu cuerpo con cada exhalación.", 600, "bienestar", '["frustrated","anxious"]', "stress", False),
        ("Meditación de la Compasión", "Metta meditation adaptada: envía amor y compasión primero a ti, luego a un ser querido, luego a un desconocido, y finalmente al mundo entero.", 600, "bienestar", '["sad","peaceful"]', "compassion", False),
        ("Visualización de Metas", "Cierra los ojos y visualiza tu vida ideal. ¿Dónde estás? ¿Qué haces? ¿Cómo te sientes? Cuanto más claro lo veas, más cerca estará de hacerse realidad.", 600, "mentalidad", '["motivated","neutral"]', "goals", True),
        ("Conexión con la Naturaleza", "Imagina que estás en tu lugar favorito de la naturaleza. Escucha los sonidos, siente la brisa, huele la tierra mojada. La naturaleza siempre sana.", 720, "bienestar", '["peaceful","neutral"]', "nature", False),
        ("Meditación del Guerrero Interior", "Conecta con tu fuerza interior. Eres un guerrero de luz. Visualiza una armadura dorada que te protege. Nada puede derribar tu espíritu.", 480, "liderazgo", '["frustrated","motivated"]', "strength", True),
        ("Relajación de Mediodía", "Un reset de 5 minutos para la mitad del día. Suelta lo que pasó en la mañana. Prepárate para una tarde productiva y en paz.", 300, "bienestar", '["neutral","frustrated"]', "reset", False),
        ("Meditación del Amor Propio", "Mírate al espejo interior con amor. Repite: 'Me acepto tal como soy. Soy suficiente. Merezco amor.' La relación más importante es contigo mismo/a.", 720, "bienestar", '["sad","neutral"]', "self-love", False),
        ("Creatividad Desbloqueada", "Abre los canales de tu creatividad. Relaja la mente analítica. Deja que las ideas fluyan como un río. La inspiración llega cuando la mente está en paz.", 600, "mentalidad", '["neutral","motivated"]', "creativity", True),
        ("Meditación para la Confianza", "Recuerda 3 momentos donde fuiste valiente. Siente esa confianza en tu pecho. Amplifica esa sensación. Tú puedes con esto.", 480, "liderazgo", '["anxious","neutral"]', "confidence", False),
        ("Soltar y Confiar", "Visualiza que escribes tus preocupaciones en hojas de papel. Luego las colocas en un río y las ves flotar. Suelta. Confía. El universo te sostiene.", 720, "bienestar", '["anxious","frustrated"]', "letting-go", False),
        ("Meditación de la Abundancia", "Tu vida ya está llena de abundancia. Hoy abrimos los ojos para verla. Cuenta tus bendiciones. La abundancia empieza con la gratitud.", 600, "mentalidad", '["grateful","happy"]', "abundance", True),
        ("Respiración 4-7-8 para Calma", "Inhala por 4 segundos. Sostén por 7 segundos. Exhala por 8 segundos. Esta técnica activa tu sistema nervioso parasimpático instantáneamente.", 300, "bienestar", '["anxious","frustrated"]', "breathing", False),
        ("El Jardín Interior", "Imagina un jardín dentro de ti. Cada flor es una cualidad tuya. Riega las que necesitan atención. Arranca las malas hierbas. Tu jardín es hermoso.", 720, "mentalidad", '["sad","peaceful"]', "self-care", False),
        ("Meditación del Servicio", "Reflexiona sobre cómo puedes servir hoy. El servicio es la forma más alta de liderazgo. Cuando ayudas a otros, te ayudas a ti mismo/a.", 480, "liderazgo", '["grateful","motivated"]', "service", False),
        ("Desconexión Digital", "Antes de dormir, desconecta tu mente de las pantallas. Respira. Cuenta tus logros del día. Agradece. Prepárate para un descanso reparador.", 600, "bienestar", '["neutral","peaceful"]', "digital-detox", False),
        ("Meditación de la Paciencia", "Roma no se construyó en un día. Tu transformación tampoco. Hoy practicamos la paciencia — contigo, con otros, con el proceso.", 480, "liderazgo", '["frustrated","neutral"]', "patience", False),
        ("Viaje al Futuro", "Viaja 5 años al futuro. ¿Dónde estás? ¿Qué lograste? ¿Cómo te sientes? Ahora regresa al presente con esa visión clara. El camino empieza hoy.", 720, "mentalidad", '["motivated","neutral"]', "vision", True),
        ("Meditación de Cierre del Día", "Repasa tu día con amor, no con juicio. ¿Qué hiciste bien? ¿Qué aprendiste? Agradece y cierra el capítulo de hoy. Mañana es una página nueva.", 600, "bienestar", '["neutral","peaceful","grateful"]', "reflection", False),
    ]

    for i, (title, desc, dur, pillar, moods, cat, premium) in enumerate(meditations):
        conn.execute(
            "INSERT INTO amp_content (id, type, title, description, content_text, duration_seconds, pillar, mood_tags, category, author, premium, sort_order) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (f"med-{i+1:03d}", "meditation", title, desc, desc, dur, pillar, moods, cat, "AMP Team", int(premium), i)
        )

    # ── MICRO-LESSONS (20) ──
    lessons = [
        ("Los 3 Pilares de una Mente Positiva", "La actitud mental positiva no es ignorar los problemas — es enfrentarlos con la certeza de que puedes superarlos. Los tres pilares son: consciencia de tus pensamientos, gratitud diaria, y acción con propósito. Hoy, practica uno.", 180, "mentalidad", '["neutral","motivated"]', "mindset"),
        ("El Arte de Liderar desde Dentro", "John Maxwell nos enseña que el liderazgo no empieza con un título. Empieza con liderarte a ti mismo. Hoy, practica tomar una decisión difícil con integridad. El mundo necesita líderes que actúen desde el corazón.", 120, "liderazgo", '["motivated","neutral"]', "leadership"),
        ("Bienestar no es un Lujo", "Tu bienestar físico y mental son la base de todo lo demás. No es egoísta priorizarte — es necesario. Hoy, dedica 10 minutos solo para ti. Sin celular. Sin pendientes. Solo tú y tu paz.", 180, "bienestar", '["neutral","peaceful"]', "wellness"),
        ("La Neurociencia de la Gratitud", "Cuando practicas gratitud, tu cerebro libera dopamina y serotonina. Es literalmente una droga natural de felicidad. Escribe 3 cosas por las que estás agradecido/a cada noche. En 21 días, tu cerebro cambiará.", 180, "mentalidad", '["grateful","neutral"]', "gratitude"),
        ("Respirar es Vivir", "La mayoría respiramos al 30% de nuestra capacidad. La respiración profunda reduce cortisol, baja la presión arterial, y calma la ansiedad. Practica: 4 segundos inhala, 4 sostén, 6 exhala. 5 veces.", 120, "bienestar", '["anxious","neutral"]', "breathing"),
        ("Los 5 Niveles de Liderazgo", "John Maxwell identifica 5 niveles: 1) Posición, 2) Permiso, 3) Producción, 4) Desarrollo de Personas, 5) Cumbre. ¿En qué nivel estás? La mayoría se queda en 1-2. El verdadero liderazgo empieza en el nivel 3.", 180, "liderazgo", '["motivated","neutral"]', "leadership"),
        ("El Poder del Ahora", "El pasado ya pasó. El futuro no existe aún. Solo tienes este momento. Cuando tu mente divague al pasado (arrepentimiento) o al futuro (ansiedad), regresa al ahora. Aquí es donde vives.", 120, "bienestar", '["anxious","neutral"]', "mindfulness"),
        ("Tu Tribu Te Define", "Eres el promedio de las 5 personas con las que más tiempo pasas. ¿Tu tribu te eleva o te hunde? Hoy, evalúa tus relaciones. Invierte en las que te hacen crecer.", 180, "liderazgo", '["neutral","motivated"]', "relationships"),
        ("La Regla del 10-10-10", "Antes de tomar una decisión difícil, pregúntate: ¿Cómo me sentiré en 10 minutos? ¿En 10 meses? ¿En 10 años? Esta perspectiva temporal te da claridad instantánea.", 120, "mentalidad", '["frustrated","neutral"]', "decision-making"),
        ("Mindful Eating", "Hoy come una comida con atención plena. Observa los colores. Siente las texturas. Saborea cada bocado. Cuando comes con consciencia, nutres el cuerpo y el alma.", 120, "bienestar", '["neutral","peaceful"]', "mindfulness"),
        ("La Ley del Espejo", "Lo que te molesta de otros es lo que no has sanado en ti. Lo que admiras en otros es lo que tienes pero no has reconocido. Los demás son tu espejo. ¿Qué ves hoy?", 180, "mentalidad", '["frustrated","neutral"]', "self-awareness"),
        ("Micro-Hábitos que Transforman", "No necesitas cambios gigantes. Necesitas micro-hábitos consistentes. 1 minuto de meditación. 1 afirmación. 1 acto de gratitud. La consistencia le gana al esfuerzo heroico.", 120, "mentalidad", '["motivated","neutral"]', "habits"),
        ("El Coraje de Ser Vulnerable", "Brené Brown dice que la vulnerabilidad no es debilidad — es valentía. Hoy, comparte algo real con alguien de confianza. La conexión humana nace de la autenticidad.", 180, "liderazgo", '["sad","neutral"]', "vulnerability"),
        ("Tu Cuerpo Habla", "Tu cuerpo almacena emociones. El estrés se acumula en los hombros. La tristeza en el pecho. El miedo en el estómago. Hoy, escucha tu cuerpo. ¿Qué te está diciendo?", 120, "bienestar", '["neutral","anxious"]', "body-awareness"),
        ("Mentalidad de Crecimiento vs. Fija", "Carol Dweck identificó dos mentalidades: fija ('no puedo') y de crecimiento ('aún no puedo'). Cambia 'no soy bueno en esto' por 'estoy aprendiendo esto.' Una palabra lo cambia todo.", 180, "mentalidad", '["frustrated","motivated"]', "growth"),
        ("El Arte de Decir No", "Cada 'sí' a algo que no te importa es un 'no' a algo que sí. Decir 'no' con amor es una forma de liderazgo personal. Hoy, practica un 'no' respetuoso.", 120, "liderazgo", '["frustrated","neutral"]', "boundaries"),
        ("Dopamina Natural", "5 formas de generar dopamina sin pantallas: 1) Ejercicio, 2) Sol directo por 10 min, 3) Completar una tarea pequeña, 4) Escuchar música, 5) Actos de bondad.", 180, "bienestar", '["sad","neutral"]', "wellness"),
        ("La Paradoja del Control", "Mientras más intentas controlar todo, más ansiedad sientes. La verdadera paz viene de aceptar lo que no puedes controlar y actuar sobre lo que sí. Hoy, suelta una cosa.", 120, "mentalidad", '["anxious","frustrated"]', "acceptance"),
        ("Liderazgo Servicial", "Los mejores líderes no mandan — sirven. ¿Cómo puedes servir hoy? No tiene que ser grande. Un mensaje de ánimo, una mano extendida, una palabra de apoyo.", 180, "liderazgo", '["grateful","motivated"]', "service"),
        ("Tu Ritual de la Noche", "Los últimos 30 minutos antes de dormir programan tu subconsciente. En lugar de redes sociales, prueba: 5 minutos de gratitud, 5 de lectura, 5 de respiración. Tu mañana empieza la noche anterior.", 120, "bienestar", '["neutral","peaceful"]', "routine"),
    ]

    for i, (title, text, dur, pillar, moods, cat) in enumerate(lessons):
        conn.execute(
            "INSERT INTO amp_content (id, type, title, description, content_text, duration_seconds, pillar, mood_tags, category, author, sort_order) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (f"les-{i+1:03d}", "lesson", title, text[:100] + "...", text, dur, pillar, moods, cat, "AMP Team", i)
        )

    # ── COURSES (5) ──
    courses_data = [
        ("course-gratitud", "21 Días de Gratitud", "Transforma tu perspectiva con 21 días de prácticas de gratitud que cambiarán cómo ves el mundo.", "mentalidad", 21, False),
        ("course-meditacion", "Meditación para Principiantes", "Aprende a meditar desde cero. Sin experiencia necesaria. Solo tú, tu respiración y la calma.", "bienestar", 14, False),
        ("course-liderazgo", "Liderazgo Personal", "Inspirado en los principios de John Maxwell. Descubre el líder que llevas dentro.", "liderazgo", 21, True),
        ("course-estres", "Manejo del Estrés y la Ansiedad", "Herramientas prácticas para cuando la vida se pone difícil.", "bienestar", 14, True),
        ("course-abundancia", "Mentalidad de Abundancia", "Cambia tu relación con la abundancia. No solo dinero — abundancia en amor, salud, tiempo y propósito.", "mentalidad", 21, True),
    ]

    gratitud_lessons = [
        "Descubriendo la Gratitud", "Gratitud por lo Simple", "Tu Cuerpo Agradecido",
        "Personas que Amas", "Gratitud en la Adversidad", "Carta de Agradecimiento",
        "Naturaleza y Gratitud", "Gratitud Financiera", "Tu Historia de Superación",
        "Medio Camino: Reflexión", "Gratitud por Ti Mismo", "Tus Talentos",
        "Momentos de Alegría", "Gratitud por los Retos", "El Poder del Perdón",
        "Gratitud en el Trabajo", "Tu Legado", "Abundancia Interior",
        "Conexiones que Sanan", "Gratitud por el Presente", "Gratitud como Estilo de Vida"
    ]
    meditacion_lessons = [
        "¿Qué es Meditar?", "Tu Primera Respiración", "Observar sin Juzgar",
        "El Cuerpo Habla", "Pensamientos como Nubes", "5 Minutos de Silencio",
        "Meditación Caminando", "Mantra Personal", "Meditación y Emociones",
        "Mindfulness en lo Cotidiano", "Meditación con Música", "Gratitud Meditada",
        "Tu Espacio Sagrado", "Meditación como Hábito"
    ]
    liderazgo_lessons = [
        "El Liderazgo Empieza Contigo", "Visión Personal", "Los 5 Niveles",
        "Influencia Positiva", "Decisiones con Integridad", "Comunicación Efectiva",
        "Empatía como Fortaleza", "Servir para Liderar", "Tu Equipo Interior",
        "Resiliencia del Líder", "Mentalidad de Crecimiento", "Liderazgo y Humildad",
        "Construir Confianza", "El Poder del Ejemplo", "Liderar en Crisis",
        "Creatividad y Liderazgo", "Delegar con Confianza", "Motivar desde el Corazón",
        "Legado de un Líder", "Tu Plan de Liderazgo", "Comienza Hoy"
    ]
    estres_lessons = [
        "Entendiendo tu Estrés", "Respiración 4-7-8", "El Cuerpo bajo Estrés",
        "Pensamientos Automáticos", "Técnica de Grounding", "Límites Saludables",
        "Movimiento y Calma", "Diario de Emociones", "Soltar el Control",
        "Autocompasión", "Rutinas que Sanan", "Pedir Ayuda",
        "Estrés como Maestro", "Tu Kit Anti-Estrés"
    ]
    abundancia_lessons = [
        "Escasez vs Abundancia", "Tus Creencias sobre el Dinero", "Abundancia en Relaciones",
        "Gratitud como Imán", "Reprogramar Creencias", "Visualización Creativa",
        "Abundancia de Tiempo", "Generosidad Estratégica", "Tu Relación con el Éxito",
        "Abundancia y Salud", "Mentalidad de Crecimiento", "Atraer Oportunidades",
        "Abundancia en el Trabajo", "Soltar la Comparación", "Abundancia Espiritual",
        "El Poder de la Intención", "Acciones de Abundancia", "Comunidad y Abundancia",
        "Abundancia Creativa", "Tu Mapa de Abundancia", "Vivir en Abundancia"
    ]

    all_lesson_sets = [gratitud_lessons, meditacion_lessons, liderazgo_lessons, estres_lessons, abundancia_lessons]

    for i, (cid, title, desc, pillar, days, premium) in enumerate(courses_data):
        conn.execute(
            "INSERT INTO amp_courses (id, title, description, pillar, duration_days, lesson_count, premium) VALUES (?,?,?,?,?,?,?)",
            (cid, title, desc, pillar, days, len(all_lesson_sets[i]), int(premium))
        )
        for j, lesson_title in enumerate(all_lesson_sets[i]):
            dur = 720 + (j % 5) * 120  # 12-20 min per lesson
            conn.execute(
                "INSERT INTO amp_lessons (id, course_id, day_number, title, description, duration_seconds) VALUES (?,?,?,?,?,?)",
                (f"{cid}-day-{j+1}", cid, j + 1, f"Día {j+1}: {lesson_title}",
                 f"Lección del día {j+1} del curso {title}.", dur)
            )

    conn.commit()
    total = conn.execute("SELECT COUNT(*) as c FROM amp_content").fetchone()["c"]
    courses_count = conn.execute("SELECT COUNT(*) as c FROM amp_courses").fetchone()["c"]
    lessons_count = conn.execute("SELECT COUNT(*) as c FROM amp_lessons").fetchone()["c"]
    conn.close()

    return {
        "status": "seeded",
        "content_items": total,
        "courses": courses_count,
        "lessons": lessons_count,
    }


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
