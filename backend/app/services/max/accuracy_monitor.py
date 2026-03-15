"""
MAX Accuracy Monitor — Tracks grounding verification results over time.
Logs every web-sourced response audit, computes accuracy stats, and
surfaces flagged (low-confidence or failed) responses.
"""
import json
import logging
import uuid
from datetime import datetime, timedelta
from collections import defaultdict

from app.db.database import get_db

logger = logging.getLogger("max.accuracy")

# ── Create audit table on import ────────────────────────────────────────
try:
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS max_response_audit (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                user_query TEXT,
                response_text TEXT,
                sources_cited TEXT,
                claims_extracted INT,
                claims_verified INT,
                claims_failed INT,
                confidence_score REAL,
                model_used TEXT,
                grounding_pass INT,
                response_time_ms INT
            )
        """)
    logger.info("max_response_audit table ready")
except Exception as e:
    logger.warning(f"Failed to create max_response_audit table: {e}")

# Add new columns for quality engine (safe — ignores if already exist)
try:
    with get_db() as conn:
        for col, coltype in [
            ("channel", "TEXT DEFAULT 'chat'"),
            ("output_type", "TEXT DEFAULT 'response'"),
            ("quality_severity", "TEXT DEFAULT 'none'"),
            ("fixed_by_engine", "INT DEFAULT 0"),
        ]:
            try:
                conn.execute(f"ALTER TABLE max_response_audit ADD COLUMN {col} {coltype}")
            except Exception:
                pass  # Column already exists
except Exception as e:
    logger.debug(f"Column migration note: {e}")


class AccuracyMonitor:
    """Logs and queries MAX grounding verification audit data."""

    def log_audit(
        self,
        user_query: str,
        response_text: str,
        verification,
        model_used: str,
        response_time_ms: int = 0,
        channel: str = "chat",
        output_type: str = "response",
        quality_severity: str = "none",
        fixed_by_engine: int = 0,
    ):
        """Log a grounding verification result to the audit table.

        Args:
            user_query: The original user message
            response_text: The final (verified) response text
            verification: VerifiedResponse dataclass from grounding_verifier
            model_used: Which AI model produced the response
            response_time_ms: How long the response took in milliseconds
        """
        try:
            claims_found = verification.claims_found
            claims_verified = verification.claims_verified
            claims_failed = verification.claims_stripped
            confidence_score = (
                claims_verified / claims_found if claims_found > 0 else 1.0
            )
            grounding_pass = 1 if verification.claims_stripped == 0 else 0

            # Extract cited sources from the response (URLs)
            import re
            urls = re.findall(r'https?://[^\s\)\]<>"\']{10,}', response_text)
            sources_cited = json.dumps(list(set(urls)))

            row_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()

            with get_db() as conn:
                conn.execute(
                    """INSERT INTO max_response_audit
                       (id, timestamp, user_query, response_text, sources_cited,
                        claims_extracted, claims_verified, claims_failed,
                        confidence_score, model_used, grounding_pass, response_time_ms,
                        channel, output_type, quality_severity, fixed_by_engine)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        row_id,
                        timestamp,
                        user_query[:2000],
                        response_text[:5000],
                        sources_cited,
                        claims_found,
                        claims_verified,
                        claims_failed,
                        confidence_score,
                        model_used or "unknown",
                        grounding_pass,
                        response_time_ms,
                        channel,
                        output_type,
                        quality_severity,
                        fixed_by_engine,
                    ),
                )

            logger.debug(
                f"Audit logged: confidence={confidence_score:.2f} "
                f"pass={bool(grounding_pass)} model={model_used}"
            )
        except Exception as e:
            logger.warning(f"Failed to log audit: {e}")

    def get_stats(self, days: int = 30) -> dict:
        """Return accuracy statistics for the last N days.

        Returns dict with:
            total_queries, accuracy_rate, avg_confidence, fail_count,
            by_model, worst_sources, trend
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        try:
            with get_db() as conn:
                # Overall stats
                row = conn.execute(
                    """SELECT
                           COUNT(*) as total,
                           SUM(grounding_pass) as passed,
                           AVG(confidence_score) as avg_conf,
                           SUM(CASE WHEN grounding_pass = 0 THEN 1 ELSE 0 END) as failed
                       FROM max_response_audit
                       WHERE timestamp >= ?""",
                    (cutoff,),
                ).fetchone()

                total = row["total"] or 0
                passed = row["passed"] or 0
                avg_conf = row["avg_conf"] or 1.0
                failed = row["failed"] or 0
                accuracy_rate = (passed / total * 100) if total > 0 else 100.0

                # By model breakdown
                model_rows = conn.execute(
                    """SELECT model_used,
                              COUNT(*) as count,
                              AVG(confidence_score) as avg_conf,
                              SUM(grounding_pass) as passed
                       FROM max_response_audit
                       WHERE timestamp >= ?
                       GROUP BY model_used""",
                    (cutoff,),
                ).fetchall()

                by_model = {}
                for mr in model_rows:
                    m_total = mr["count"]
                    m_passed = mr["passed"] or 0
                    by_model[mr["model_used"]] = {
                        "total": m_total,
                        "accuracy_rate": (m_passed / m_total * 100) if m_total > 0 else 100.0,
                        "avg_confidence": mr["avg_conf"] or 1.0,
                    }

                # By channel breakdown
                channel_rows = conn.execute(
                    """SELECT channel,
                              COUNT(*) as count,
                              SUM(grounding_pass) as passed,
                              SUM(fixed_by_engine) as fixed
                       FROM max_response_audit
                       WHERE timestamp >= ?
                       GROUP BY channel""",
                    (cutoff,),
                ).fetchall()

                by_channel = {}
                for cr in channel_rows:
                    c_total = cr["count"]
                    c_passed = cr["passed"] or 0
                    by_channel[cr["channel"] or "chat"] = {
                        "total": c_total,
                        "accuracy_rate": (c_passed / c_total * 100) if c_total > 0 else 100.0,
                        "auto_fixed": cr["fixed"] or 0,
                    }

                # Worst sources (domains with most phantom citations)
                source_rows = conn.execute(
                    """SELECT sources_cited, claims_failed
                       FROM max_response_audit
                       WHERE timestamp >= ? AND claims_failed > 0""",
                    (cutoff,),
                ).fetchall()

                domain_phantoms = defaultdict(int)
                for sr in source_rows:
                    try:
                        urls = json.loads(sr["sources_cited"] or "[]")
                        import re
                        for url in urls:
                            match = re.search(r'https?://(?:www\.)?([^/]+)', url)
                            if match:
                                domain_phantoms[match.group(1).lower()] += sr["claims_failed"]
                    except (json.JSONDecodeError, TypeError):
                        pass

                worst_sources = sorted(
                    [{"domain": d, "phantom_count": c} for d, c in domain_phantoms.items()],
                    key=lambda x: x["phantom_count"],
                    reverse=True,
                )[:10]

                # Trend: daily accuracy for last N days
                trend_rows = conn.execute(
                    """SELECT DATE(timestamp) as day,
                              COUNT(*) as total,
                              SUM(grounding_pass) as passed
                       FROM max_response_audit
                       WHERE timestamp >= ?
                       GROUP BY DATE(timestamp)
                       ORDER BY day""",
                    (cutoff,),
                ).fetchall()

                trend = []
                for tr in trend_rows:
                    t_total = tr["total"]
                    t_passed = tr["passed"] or 0
                    trend.append({
                        "date": tr["day"],
                        "total": t_total,
                        "accuracy": (t_passed / t_total * 100) if t_total > 0 else 100.0,
                    })

                return {
                    "total_queries": total,
                    "accuracy_rate": accuracy_rate,
                    "avg_confidence": avg_conf,
                    "fail_count": failed,
                    "by_model": by_model,
                    "by_channel": by_channel,
                    "worst_sources": worst_sources,
                    "trend": trend,
                }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "total_queries": 0,
                "accuracy_rate": 100.0,
                "avg_confidence": 1.0,
                "fail_count": 0,
                "by_model": {},
                "by_channel": {},
                "worst_sources": [],
                "trend": [],
            }

    def get_log(
        self,
        page: int = 1,
        per_page: int = 50,
        model: str | None = None,
        passed: bool | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict:
        """Return paginated audit log with optional filters.

        Returns dict with: items (list of audit rows), total, page, per_page
        """
        try:
            conditions = []
            params = []

            if model:
                conditions.append("model_used = ?")
                params.append(model)
            if passed is not None:
                conditions.append("grounding_pass = ?")
                params.append(1 if passed else 0)
            if date_from:
                conditions.append("timestamp >= ?")
                params.append(date_from)
            if date_to:
                conditions.append("timestamp <= ?")
                params.append(date_to)

            where = ""
            if conditions:
                where = "WHERE " + " AND ".join(conditions)

            with get_db() as conn:
                # Count
                count_row = conn.execute(
                    f"SELECT COUNT(*) as cnt FROM max_response_audit {where}",
                    params,
                ).fetchone()
                total = count_row["cnt"] or 0

                # Paginated results
                offset = (page - 1) * per_page
                rows = conn.execute(
                    f"""SELECT * FROM max_response_audit {where}
                        ORDER BY timestamp DESC
                        LIMIT ? OFFSET ?""",
                    params + [per_page, offset],
                ).fetchall()

                items = []
                for r in rows:
                    item = dict(r)
                    # Parse sources_cited back to list
                    try:
                        item["sources_cited"] = json.loads(item.get("sources_cited") or "[]")
                    except (json.JSONDecodeError, TypeError):
                        item["sources_cited"] = []
                    item["grounding_pass"] = bool(item.get("grounding_pass"))
                    items.append(item)

                return {
                    "items": items,
                    "total": total,
                    "page": page,
                    "per_page": per_page,
                }

        except Exception as e:
            logger.error(f"Failed to get log: {e}")
            return {"items": [], "total": 0, "page": page, "per_page": per_page}

    def get_flagged(self, limit: int = 50) -> list:
        """Return responses that failed grounding or have low confidence.

        Flagged = grounding_pass == 0 OR confidence_score < 0.6
        """
        try:
            with get_db() as conn:
                rows = conn.execute(
                    """SELECT * FROM max_response_audit
                       WHERE grounding_pass = 0 OR confidence_score < 0.6
                       ORDER BY timestamp DESC
                       LIMIT ?""",
                    (limit,),
                ).fetchall()

                items = []
                for r in rows:
                    item = dict(r)
                    try:
                        item["sources_cited"] = json.loads(item.get("sources_cited") or "[]")
                    except (json.JSONDecodeError, TypeError):
                        item["sources_cited"] = []
                    item["grounding_pass"] = bool(item.get("grounding_pass"))
                    items.append(item)

                return items

        except Exception as e:
            logger.error(f"Failed to get flagged: {e}")
            return []


# Singleton
accuracy_monitor = AccuracyMonitor()
