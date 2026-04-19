"""
MAX Answer Evaluation Loop — persistent tracking of response quality,
user feedback, implicit signals, and routing preferences.

Tracks:
- Per-response evaluation (channel, intent, capability, model, tools, latency)
- Explicit feedback (thumbs up/down, rating, tags)
- Implicit signals (retries, corrections, dissatisfaction markers)
- Rolling aggregates for provider/tool/channel performance

Does NOT modify routing blindly — exposes metrics for smarter routing decisions.
"""
import json
import logging
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger("max.evaluation")

# ── Database path ────────────────────────────────────────────────────

def _get_db_path() -> Path:
    """DB stored at backend/data/empire.db."""
    return Path(__file__).resolve().parents[3] / "data" / "empire.db"


# ── Schema initialization ────────────────────────────────────────────

def init_evaluation_schema(db_path: Path = None):
    import sqlite3
    if db_path is None:
        db_path = _get_db_path()

    with sqlite3.connect(db_path) as conn:
        # Primary response evaluation record
        conn.execute("""
            CREATE TABLE IF NOT EXISTS max_response_evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                response_id TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                -- Request context
                channel TEXT DEFAULT 'chat',
                conversation_id TEXT,
                intent TEXT,
                capability TEXT,
                has_image INTEGER DEFAULT 0,

                -- Model/provider info
                model_used TEXT,
                provider TEXT,
                fallback_used INTEGER DEFAULT 0,

                -- Tool execution
                tools_used TEXT,           -- JSON list of tool names
                tool_results TEXT,         -- JSON list of {tool, success} results
                any_tool_failure INTEGER DEFAULT 0,

                -- Latency and outcome
                latency_ms INTEGER,
                response_length INTEGER,

                -- Outcome (can be updated later)
                outcome TEXT DEFAULT 'unknown',  -- success|failure|partial|unknown

                -- Explicit feedback
                feedback_submitted INTEGER DEFAULT 0,

                -- Implicit signals
                implicit_signals TEXT,      -- JSON: retry, correction, dissatisfaction_markers
                user_corrected INTEGER DEFAULT 0,
                repeated_ask INTEGER DEFAULT 0,

                -- Separate scoring dimensions
                correctness_score REAL,     -- 0.0–1.0, accuracy of information
                satisfaction_score REAL,    -- 0.0–1.0, user satisfaction
                outcome_score REAL          -- 0.0–1.0, task completion quality
            )
        """)

        # Explicit user feedback
        conn.execute("""
            CREATE TABLE IF NOT EXISTS max_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                response_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                thumbs_up INTEGER DEFAULT 0,   -- 1 = up, 0 = down, NULL = not set
                rating INTEGER,                  -- 1–5, NULL = not set

                -- Tags
                tag_helpful INTEGER DEFAULT 0,
                tag_wrong INTEGER DEFAULT 0,
                tag_incomplete INTEGER DEFAULT 0,
                tag_too_slow INTEGER DEFAULT 0,
                tag_wrong_tool INTEGER DEFAULT 0,
                tag_stale INTEGER DEFAULT 0,
                tag_should_have_searched INTEGER DEFAULT 0,
                tag_should_have_used_image INTEGER DEFAULT 0,

                -- Freeform
                comment TEXT,

                -- Link to evaluation
                FOREIGN KEY (response_id) REFERENCES max_response_evaluations(response_id)
            )
        """)

        # Rolling aggregates for routing decisions
        conn.execute("""
            CREATE TABLE IF NOT EXISTS max_routing_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                -- Key: composite of provider + capability
                provider TEXT NOT NULL,
                capability TEXT NOT NULL,

                -- Rolling window stats (30 days)
                total_requests INTEGER DEFAULT 0,
                successful_requests INTEGER DEFAULT 0,
                satisfaction_sum REAL DEFAULT 0,
                satisfaction_count INTEGER DEFAULT 0,
                avg_latency_ms REAL DEFAULT 0,
                retry_count INTEGER DEFAULT 0,
                correction_count INTEGER DEFAULT 0,

                -- Computed scores (0.0–1.0)
                success_rate REAL DEFAULT 0.0,
                satisfaction_rate REAL DEFAULT 0.0,
                retry_rate REAL DEFAULT 0.0,
                correction_rate REAL DEFAULT 0.0,

                UNIQUE(provider, capability)
            )
        """)

        # Tool performance by capability
        conn.execute("""
            CREATE TABLE IF NOT EXISTS max_tool_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                tool_name TEXT NOT NULL,
                capability TEXT NOT NULL,

                total_calls INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                avg_latency_ms REAL DEFAULT 0,

                success_rate REAL DEFAULT 0.0,

                UNIQUE(tool_name, capability)
            )
        """)

        conn.commit()
    logger.info("[evaluation] Schema initialized")


# ── Evaluation Service ────────────────────────────────────────────────

class EvaluationService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.db_path = _get_db_path()
        self._ensure_schema()

    def _ensure_schema(self):
        try:
            init_evaluation_schema(self.db_path)
        except Exception as e:
            logger.warning(f"[evaluation] Schema init failed (may already exist): {e}")

    # ── Intent Classification ─────────────────────────────────────────

    INTENT_PATTERNS = {
        "quote": ["quote", "price", "pricing", "cost", "estimate", "how much"],
        "image_understanding": ["image", "photo", "picture", "what is", "describe", "look at", "see this"],
        "email": ["email", "send email", "check email", "inbox", "gmail"],
        "task": ["task", "todo", "reminder", "schedule", "create task"],
        "git": ["git", "commit", "push", "pull", "branch"],
        "code": ["code", "fix", "edit", "file", "write code", "refactor"],
        "search": ["search", "find", "look up", "web search"],
        "payment": ["pay", "invoice", "payment", "stripe", "charge"],
        "production": ["production", "job", "work order", "manufacturing"],
        "drawing": ["draw", "drawing", "render", "blueprint", "window", "bench"],
        "telegram": ["telegram", "send to", "message on telegram"],
        "web": ["web", "website", "url", "link"],
        "presentation": ["presentation", "present", "generate a presentation", "create a presentation", "make a presentation", "briefing", "research document", "report on", "topic report"],
        "chat": [],  # default
    }

    def classify_intent(self, message: str) -> str:
        """Classify the intent of a user message."""
        msg = message.lower()
        for intent, patterns in self.INTENT_PATTERNS.items():
            if any(p in msg for p in patterns):
                return intent
        return "chat"

    def detect_capability_from_message(self, message: str, has_image: bool = False, tools_used: list = None) -> str:
        """Detect which capability was likely used for this response."""
        if has_image or "image" in message.lower():
            return "understand_image"
        if tools_used:
            # Return first non-trivial tool
            for t in tools_used:
                if t not in ("run_desk_task", "web_read", "web_search"):
                    return t
        return self.classify_intent(message)

    # ── Provider mapping ──────────────────────────────────────────────

    def get_provider(self, model: str) -> str:
        """Map model name to provider name."""
        if not model:
            return "unknown"
        model = model.lower()
        if "grok" in model or model.startswith("xai"):
            return "xai"
        if "claude" in model:
            return "anthropic"
        if "gpt" in model or "openai" in model:
            return "openai"
        if "groq" in model or "llama" in model:
            return "groq"
        if "gemini" in model:
            return "google"
        if "ollama" in model or "llama" in model:
            return "ollama"
        if "openclaw" in model:
            return "openclaw"
        return "unknown"

    # ── Core logging ─────────────────────────────────────────────────

    def log_response(
        self,
        response_id: str,
        channel: str,
        conversation_id: str,
        message: str,
        model_used: str,
        tools_used: list,
        tool_results: list,
        latency_ms: int,
        response_length: int,
        fallback_used: bool,
    ) -> str:
        """Log a MAX response for evaluation. Returns the response_id."""
        import sqlite3
        if not response_id:
            response_id = str(uuid.uuid4())[:12]

        intent = self.classify_intent(message)
        has_image = 1 if any("image" in t.lower() or "photo" in t.lower() for t in tools_used) else 0
        capability = self.detect_capability_from_message(message, has_image=has_image, tools_used=tools_used)
        provider = self.get_provider(model_used)
        any_tool_failure = 1 if any(not r.get("success", False) for r in tool_results) else 0

        # Detect implicit signals
        implicit = self._detect_implicit_signals(message, tool_results)
        user_corrected = 1 if implicit.get("correction", False) else 0
        repeated_ask = 1 if implicit.get("retry", False) else 0

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR IGNORE INTO max_response_evaluations
                    (response_id, channel, conversation_id, intent, capability, has_image,
                     model_used, provider, fallback_used, tools_used, tool_results,
                     any_tool_failure, latency_ms, response_length, user_corrected, repeated_ask,
                     implicit_signals)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    response_id, channel, conversation_id or None, intent, capability, has_image,
                    model_used, provider, 1 if fallback_used else 0,
                    json.dumps(tools_used), json.dumps(tool_results),
                    any_tool_failure, latency_ms, response_length, user_corrected, repeated_ask,
                    json.dumps(implicit),
                ))

                # Update routing preferences aggregates
                self._update_routing_preferences(conn, provider, capability, latency_ms, any_tool_failure, fallback_used)

                # Update tool performance
                for tool_name in tools_used:
                    self._update_tool_performance(conn, tool_name, capability, tool_results, latency_ms)

            logger.debug(f"[evaluation] Logged response {response_id}: {intent}/{capability} via {provider}")
        except Exception as e:
            logger.warning(f"[evaluation] log_response failed: {e}")

        return response_id

    def _detect_implicit_signals(self, message: str, tool_results: list) -> dict:
        """Detect implicit dissatisfaction or success signals from message and tool results."""
        msg_lower = message.lower()
        signals = {}

        # Correction patterns: user is correcting a previous wrong answer
        correction_patterns = [
            "that's wrong", "that was wrong", "incorrect", "not right",
            "actually", "i said", "i meant", "wait", "hold on",
            "you misunderstood", "that's not what i asked",
        ]
        signals["correction"] = any(p in msg_lower for p in correction_patterns)

        # Retry/repeated ask: user asked the same thing again
        retry_patterns = ["again", "repeat", "same thing", "once more", "another time"]
        signals["retry"] = any(p in msg_lower for p in retry_patterns)

        # Dissatisfaction markers
        dissatisfaction = []
        if any(p in msg_lower for p in ["still not", "didn't work", "not working", "failed", "error"]):
            dissatisfaction.append("error_reported")
        if any(p in msg_lower for p in ["too slow", "taking too long", "慢", "wait"]):
            dissatisfaction.append("too_slow")
        if any(p in msg_lower for p in ["wrong", "incorrect", "bad", "terrible"]):
            dissatisfaction.append("quality_complaint")

        signals["dissatisfaction_markers"] = dissatisfaction

        # Success signals: follow-through indicators
        signals["success_indicator"] = any(
            p in msg_lower for p in ["thanks", "great", "perfect", "that worked", "works now", "good"]
        )

        return signals

    def _update_routing_preferences(self, conn, provider: str, capability: str, latency_ms: int, any_failure: int, fallback_used: bool):
        """Update rolling aggregates for provider+capability."""
        window_days = 30
        cutoff = (datetime.now() - timedelta(days=window_days)).isoformat()

        # Get existing aggregate
        row = conn.execute(
            "SELECT total_requests, satisfaction_sum, satisfaction_count, avg_latency_ms, retry_count, correction_count FROM max_routing_preferences WHERE provider=? AND capability=?",
            (provider, capability)
        ).fetchone()

        if row:
            total, sat_sum, sat_count, avg_lat, retry_ct, corr_ct = row
            new_total = total + 1
            # Rolling average for latency
            new_avg_lat = ((avg_lat * total) + latency_ms) / new_total if total > 0 else latency_ms
            new_retry = retry_ct + (1 if fallback_used else 0)
            new_corr = corr_ct  # corrections tracked separately via feedback
        else:
            new_total = 1
            sat_sum = 0.0
            sat_count = 0
            new_avg_lat = float(latency_ms)
            new_retry = 1 if fallback_used else 0
            new_corr = 0

        # Compute rates
        success_rate = 1.0 - (any_failure / new_total) if new_total > 0 else 0.0
        retry_rate = new_retry / new_total if new_total > 0 else 0.0

        conn.execute("""
            INSERT INTO max_routing_preferences
            (provider, capability, total_requests, successful_requests, satisfaction_sum,
             satisfaction_count, avg_latency_ms, retry_count, correction_count,
             success_rate, satisfaction_rate, retry_rate, correction_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(provider, capability) DO UPDATE SET
                total_requests=excluded.total_requests,
                successful_requests=excluded.successful_requests,
                satisfaction_sum=excluded.satisfaction_sum,
                satisfaction_count=excluded.satisfaction_count,
                avg_latency_ms=excluded.avg_latency_ms,
                retry_count=excluded.retry_count,
                correction_count=excluded.correction_count,
                success_rate=excluded.success_rate,
                satisfaction_rate=excluded.satisfaction_rate,
                retry_rate=excluded.retry_rate,
                correction_rate=excluded.correction_rate,
                updated_at=CURRENT_TIMESTAMP
        """, (
            provider, capability, new_total,
            new_total - any_failure, sat_sum, sat_count,
            new_avg_lat, new_retry, new_corr,
            success_rate, 0.0, retry_rate, 0.0,
        ))

    def _update_tool_performance(self, conn, tool_name: str, capability: str, tool_results: list, latency_ms: int):
        """Update tool performance aggregate."""
        # Count this tool's results
        tool_successes = sum(1 for r in tool_results if r.get("tool") == tool_name and r.get("success"))
        tool_failures = sum(1 for r in tool_results if r.get("tool") == tool_name and not r.get("success"))

        row = conn.execute(
            "SELECT total_calls, success_count, failure_count, avg_latency_ms FROM max_tool_performance WHERE tool_name=? AND capability=?",
            (tool_name, capability)
        ).fetchone()

        if row:
            total, successes, failures, avg_lat = row
            new_total = total + tool_successes + tool_failures
            new_successes = successes + tool_successes
            new_failures = failures + tool_failures
            new_avg_lat = ((avg_lat * total) + latency_ms) / new_total if total > 0 else latency_ms
        else:
            new_total = tool_successes + tool_failures
            new_successes = tool_successes
            new_failures = tool_failures
            new_avg_lat = float(latency_ms)

        success_rate = new_successes / new_total if new_total > 0 else 0.0

        conn.execute("""
            INSERT INTO max_tool_performance
            (tool_name, capability, total_calls, success_count, failure_count, avg_latency_ms, success_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tool_name, capability) DO UPDATE SET
                total_calls=excluded.total_calls,
                success_count=excluded.success_count,
                failure_count=excluded.failure_count,
                avg_latency_ms=excluded.avg_latency_ms,
                success_rate=excluded.success_rate,
                updated_at=CURRENT_TIMESTAMP
        """, (tool_name, capability, new_total, new_successes, new_failures, new_avg_lat, success_rate))

    # ── Explicit Feedback ─────────────────────────────────────────────

    def submit_feedback(
        self,
        response_id: str,
        thumbs_up: int = None,
        rating: int = None,
        tag_helpful: bool = False,
        tag_wrong: bool = False,
        tag_incomplete: bool = False,
        tag_too_slow: bool = False,
        tag_wrong_tool: bool = False,
        tag_stale: bool = False,
        tag_should_have_searched: bool = False,
        tag_should_have_used_image: bool = False,
        comment: str = None,
    ) -> bool:
        """Submit explicit feedback for a response."""
        import sqlite3

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Insert feedback
                conn.execute("""
                    INSERT INTO max_feedback
                    (response_id, thumbs_up, rating, tag_helpful, tag_wrong, tag_incomplete,
                     tag_too_slow, tag_wrong_tool, tag_stale, tag_should_have_searched,
                     tag_should_have_used_image, comment)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    response_id, thumbs_up, rating,
                    1 if tag_helpful else 0, 1 if tag_wrong else 0,
                    1 if tag_incomplete else 0, 1 if tag_too_slow else 0,
                    1 if tag_wrong_tool else 0, 1 if tag_stale else 0,
                    1 if tag_should_have_searched else 0, 1 if tag_should_have_used_image else 0,
                    comment,
                ))

                # Mark evaluation as having feedback
                conn.execute(
                    "UPDATE max_response_evaluations SET feedback_submitted=1 WHERE response_id=?",
                    (response_id,)
                )

                # Update satisfaction score if rating provided
                if rating is not None and 1 <= rating <= 5:
                    satisfaction = (rating - 1) / 4.0  # Map 1-5 → 0.0-1.0
                    conn.execute(
                        "UPDATE max_response_evaluations SET satisfaction_score=? WHERE response_id=?",
                        (satisfaction, response_id)
                    )
                    # Also update routing preferences
                    ev = conn.execute(
                        "SELECT provider, capability FROM max_response_evaluations WHERE response_id=?",
                        (response_id,)
                    ).fetchone()
                    if ev:
                        provider, capability = ev
                        conn.execute("""
                            UPDATE max_routing_preferences
                            SET satisfaction_sum=satisfaction_sum+?,
                                satisfaction_count=satisfaction_count+1,
                                satisfaction_rate=(satisfaction_sum+?)/(satisfaction_count+1)
                            WHERE provider=? AND capability=?
                        """, (satisfaction, satisfaction, provider or "unknown", capability or "unknown"))

                # Update outcome based on thumbs
                if thumbs_up is not None:
                    outcome = "success" if thumbs_up else "failure"
                    conn.execute(
                        "UPDATE max_response_evaluations SET outcome=? WHERE response_id=?",
                        (outcome, response_id)
                    )

            logger.info(f"[evaluation] Feedback submitted for {response_id}: thumbs={thumbs_up}, rating={rating}")
            return True
        except Exception as e:
            logger.warning(f"[evaluation] submit_feedback failed: {e}")
            return False

    # ── Stats ─────────────────────────────────────────────────────────

    def get_routing_preferences(self, days: int = 30) -> list:
        """Get provider performance by capability for routing decisions."""
        import sqlite3
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT provider, capability, total_requests, success_rate,
                           satisfaction_rate, avg_latency_ms, retry_rate, correction_rate,
                           success_rate * 0.4 + satisfaction_rate * 0.3 + (1.0 - retry_rate) * 0.3 AS weighted_score
                    FROM max_routing_preferences
                    ORDER BY weighted_score DESC
                """).fetchall()

            return [
                {
                    "provider": r[0],
                    "capability": r[1],
                    "total_requests": r[2],
                    "success_rate": round(r[3], 3) if r[3] else 0.0,
                    "satisfaction_rate": round(r[4], 3) if r[4] else 0.0,
                    "avg_latency_ms": round(r[5], 0) if r[5] else 0,
                    "retry_rate": round(r[6], 3) if r[6] else 0.0,
                    "correction_rate": round(r[7], 3) if r[7] else 0.0,
                    "weighted_score": round(r[8], 3) if r[8] else 0.0,
                }
                for r in rows
            ]
        except Exception as e:
            logger.warning(f"[evaluation] get_routing_preferences failed: {e}")
            return []

    def get_tool_performance(self, days: int = 30) -> list:
        """Get tool performance by capability."""
        import sqlite3
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT tool_name, capability, total_calls, success_rate, avg_latency_ms
                    FROM max_tool_performance
                    ORDER BY success_rate ASC
                """).fetchall()

            return [
                {
                    "tool": r[0],
                    "capability": r[1],
                    "total_calls": r[2],
                    "success_rate": round(r[3], 3) if r[3] else 0.0,
                    "avg_latency_ms": round(r[4], 0) if r[4] else 0,
                }
                for r in rows
            ]
        except Exception as e:
            logger.warning(f"[evaluation] get_tool_performance failed: {e}")
            return []

    def get_frustration_hotspots(self, days: int = 30) -> dict:
        """Find most common failure and frustration patterns."""
        import sqlite3
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Top frustrations by tag
                tag_counts = conn.execute("""
                    SELECT
                        CASE
                            WHEN tag_wrong=1 THEN 'wrong'
                            WHEN tag_incomplete=1 THEN 'incomplete'
                            WHEN tag_too_slow=1 THEN 'too_slow'
                            WHEN tag_wrong_tool=1 THEN 'wrong_tool'
                            WHEN tag_stale=1 THEN 'stale'
                            WHEN tag_should_have_searched=1 THEN 'should_have_searched'
                            WHEN tag_should_have_used_image=1 THEN 'should_have_used_image'
                        END as tag,
                        COUNT(*) as count
                    FROM max_feedback f
                    JOIN max_response_evaluations e ON f.response_id = e.response_id
                    WHERE f.thumbs_up = 0 AND tag IS NOT NULL
                    GROUP BY tag
                    ORDER BY count DESC
                    LIMIT 10
                """).fetchall()

                # Low satisfaction providers
                low_sat = conn.execute("""
                    SELECT provider, capability, satisfaction_rate, total_requests
                    FROM max_routing_preferences
                    WHERE satisfaction_rate < 0.7 AND total_requests >= 3
                    ORDER BY satisfaction_rate ASC
                    LIMIT 10
                """).fetchall()

                # High retry providers
                high_retry = conn.execute("""
                    SELECT provider, capability, retry_rate, total_requests
                    FROM max_routing_preferences
                    WHERE retry_rate > 0.2 AND total_requests >= 3
                    ORDER BY retry_rate DESC
                    LIMIT 10
                """).fetchall()

            return {
                "top_frustration_tags": [{"tag": r[0], "count": r[1]} for r in tag_counts],
                "low_satisfaction_providers": [
                    {"provider": r[0], "capability": r[1], "satisfaction_rate": round(r[2], 3), "total_requests": r[3]}
                    for r in low_sat
                ],
                "high_retry_providers": [
                    {"provider": r[0], "capability": r[1], "retry_rate": round(r[2], 3), "total_requests": r[3]}
                    for r in high_retry
                ],
            }
        except Exception as e:
            logger.warning(f"[evaluation] get_frustration_hotspots failed: {e}")
            return {"top_frustration_tags": [], "low_satisfaction_providers": [], "high_retry_providers": []}

    def get_recent_evaluations(self, limit: int = 20) -> list:
        """Get recent evaluations for inspection."""
        import sqlite3
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT e.response_id, e.created_at, e.channel, e.intent, e.capability,
                           e.model_used, e.provider, e.outcome, e.latency_ms,
                           e.satisfaction_score, e.correctness_score, e.outcome_score,
                           e.any_tool_failure, e.user_corrected, e.repeated_ask,
                           f.thumbs_up, f.rating, f.tag_helpful, f.tag_wrong
                    FROM max_response_evaluations e
                    LEFT JOIN max_feedback f ON e.response_id = f.response_id
                    ORDER BY e.created_at DESC
                    LIMIT ?
                """, (limit,)).fetchall()

            return [
                {
                    "response_id": r[0],
                    "created_at": r[1],
                    "channel": r[2],
                    "intent": r[3],
                    "capability": r[4],
                    "model_used": r[5],
                    "provider": r[6],
                    "outcome": r[7],
                    "latency_ms": r[8],
                    "satisfaction_score": round(r[9], 3) if r[9] else None,
                    "correctness_score": round(r[10], 3) if r[10] else None,
                    "outcome_score": round(r[11], 3) if r[11] else None,
                    "tool_failure": bool(r[12]),
                    "user_corrected": bool(r[13]),
                    "repeated_ask": bool(r[14]),
                    "thumbs_up": bool(r[15]) if r[15] is not None else None,
                    "rating": r[16],
                    "tag_helpful": bool(r[17]),
                    "tag_wrong": bool(r[18]),
                }
                for r in rows
            ]
        except Exception as e:
            logger.warning(f"[evaluation] get_recent_evaluations failed: {e}")
            return []


# ── Singleton ─────────────────────────────────────────────────────────

evaluation_service = EvaluationService()
