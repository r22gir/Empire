import json
import sqlite3

from app.services.max.evaluation_loop_v1 import (
    get_recent_scores,
    init_score_schema,
    run_evaluation_loop_v1,
)


def _seed_eval_row(db_path, response_id, channel, metadata):
    init_score_schema(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO max_response_evaluations
               (response_id, channel, conversation_id, model_used, tools_used, tool_results,
                any_tool_failure, latency_ms, response_length, metadata_envelope)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                response_id,
                channel,
                "conv",
                "empire-runtime-truth-check" if metadata.get("skill_used") else "grok",
                json.dumps(["empire_runtime_truth_check"] if metadata.get("skill_used") else []),
                json.dumps([{"tool": "empire_runtime_truth_check", "success": True}] if metadata.get("skill_used") else []),
                0,
                100,
                200,
                json.dumps(metadata),
            ),
        )
        conn.commit()


def _seed_ledger(ledger_path):
    with sqlite3.connect(ledger_path) as conn:
        conn.execute(
            """CREATE TABLE unified_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                channel TEXT,
                role TEXT,
                model TEXT,
                tool_results TEXT,
                metadata TEXT
            )"""
        )
        for channel in ["web_chat", "telegram", "email"]:
            conn.execute(
                """INSERT INTO unified_messages (channel, role, model, tool_results, metadata)
                   VALUES (?, 'assistant', 'ledger-proof', '[]', ?)""",
                (channel, json.dumps({"surface": {"web_chat": "Founder/Web MAX", "telegram": "Telegram MAX", "email": "Email MAX"}[channel]})),
            )
        conn.commit()


def test_evaluation_loop_scores_and_writes_back(tmp_path):
    db_path = tmp_path / "empire.db"
    ledger_path = tmp_path / "unified_messages.db"
    _seed_eval_row(db_path, "resp-web", "web_chat", {
        "registry_version": "operating-registry-v2",
        "surface": "Founder/Web MAX",
        "skill_used": "empire_runtime_truth_check",
    })
    _seed_eval_row(db_path, "resp-tg", "telegram", {
        "registry_version": "operating-registry-v2",
        "surface": "Telegram MAX",
    })
    _seed_ledger(ledger_path)

    result = run_evaluation_loop_v1(min_count=5, db_path=db_path, ledger_path=ledger_path)
    scores = get_recent_scores(limit=10, db_path=db_path)

    assert result["scored_count"] >= 5
    assert {"web_chat", "telegram", "email"}.issubset(set(result["surfaces"]))
    assert len(scores) >= 5
    assert all("overall_score" in score for score in scores)
    assert any(score["channel"] == "email" for score in scores)
