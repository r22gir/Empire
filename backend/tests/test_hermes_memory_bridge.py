from app.services.max.continuity_compaction import build_session_handoff_packet
from app.services.max.hermes_memory import (
    ensure_hermes_memory_scaffold,
    get_hermes_memory_status,
    read_hermes_memory,
    render_hermes_bridge_for_prompt,
    write_context_from_verified_session,
)


def test_hermes_memory_scaffold_is_created_and_read_in_order(monkeypatch, tmp_path):
    root = tmp_path / "empire-box-memory"
    monkeypatch.setenv("EMPIRE_BOX_MEMORY_DIR", str(root))

    scaffold = ensure_hermes_memory_scaffold()
    bundle = read_hermes_memory()
    status = get_hermes_memory_status()
    compact = render_hermes_bridge_for_prompt(compact=True)

    assert scaffold["root"] == str(root)
    assert (root / "CONTEXT.md").exists()
    assert (root / "MEMORY.md").exists()
    assert (root / "USER.md").exists()
    assert (root / "SKILLS").is_dir()
    assert bundle["read_order"] == ["CONTEXT.md", "MEMORY.md", "USER.md"]
    assert bundle["context"]["writer"] == "max_only"
    assert bundle["memory"]["authority"] == "supporting_recall_only"
    assert bundle["user"]["authority"] == "supporting_founder_preferences_only"
    assert status["exists"] is True
    assert "Hermes Memory Bridge" in compact
    assert "CONTEXT.md -> MEMORY.md -> USER.md" in compact
    assert "CONTEXT.md is MAX-written after verified sessions." in compact


def test_verified_session_write_refreshes_context_file(monkeypatch, tmp_path):
    root = tmp_path / "empire-box-memory"
    monkeypatch.setenv("EMPIRE_BOX_MEMORY_DIR", str(root))

    packet = build_session_handoff_packet(
        current_task="Bootstrap Hermes bridge",
        channel="web",
        last_runtime_truth_result={
            "commit": "abc1234",
            "restart_required": False,
            "openclaw_gate": {"state": "healthy"},
        },
        product_statuses={"max": "active_partial", "openclaw": "healthy"},
        known_limitations=["Email continuity remains partial."],
    )
    result = write_context_from_verified_session(
        runtime_truth={
            "current_commit": {"hash": "abc1234"},
            "restart_required": False,
            "openclaw_gate": {"state": "healthy"},
        },
        packet=packet,
        channel="mobile_browser",
    )

    content = (root / "CONTEXT.md").read_text(encoding="utf-8")

    assert result["written"] is True
    assert result["path"] == str(root / "CONTEXT.md")
    assert result["surface"] == "web_chat"
    assert "Hermes reads it first and never writes it." in content
    assert "runtime > registry > repo truth > Hermes memory > skills" in content
    assert "Running commit hash: abc1234" in content
    assert "Registry version: operating-registry-v2" in content
    assert "- max: active_partial" in content
    assert "- openclaw: healthy" in content
