"""Studio frozen-gate flow: two passes to keep, one fail rejects, Night Lab yes/no."""
from __future__ import annotations

from app.services.max.studio_frozen_gate import (
    GATE_NAME,
    decide_keep_change,
    evaluate_studio_frozen_gate,
    format_gate_log_line,
)


def _run(ok: bool, **extra):
    def _fn(*, env=None, extra_args=None):
        return {"ok": ok, "returncode": 0 if ok else 1, "output": "ok" if ok else "FAILED", **extra}
    return _fn


def test_gate_yes_only_after_two_passes():
    calls = {"n": 0}

    def runner(*, env=None, extra_args=None):
        calls["n"] += 1
        return {"ok": True, "returncode": 0, "output": "10 passed"}

    out = evaluate_studio_frozen_gate(runner=runner)
    assert calls["n"] == 2
    assert out["keep"] is True
    assert out["verdict"] == "YES"
    assert out["passes"] == 2
    assert out["log_line"].startswith(f"{GATE_NAME}: YES")
    assert out["outbound"] is False


def test_gate_no_on_first_fail_does_not_run_second():
    calls = {"n": 0}

    def runner(*, env=None, extra_args=None):
        calls["n"] += 1
        return {"ok": False, "returncode": 1, "output": "FAILED"}

    out = evaluate_studio_frozen_gate(runner=runner)
    assert calls["n"] == 1
    assert out["keep"] is False
    assert out["verdict"] == "NO"
    assert out["log_line"].startswith(f"{GATE_NAME}: NO")


def test_gate_no_if_second_pass_fails():
    calls = {"n": 0}

    def runner(*, env=None, extra_args=None):
        calls["n"] += 1
        return {"ok": calls["n"] == 1, "returncode": 0 if calls["n"] == 1 else 1, "output": str(calls["n"])}

    out = evaluate_studio_frozen_gate(runner=runner)
    assert calls["n"] == 2
    assert out["keep"] is False
    assert out["verdict"] == "NO"
    assert out["passes"] == 1
    assert "pass 2" in out["log_line"]


def test_decide_keep_reverts_bad_change():
    state = {"value": "clean"}

    def apply():
        state["value"] = "bad"

    def revert():
        state["value"] = "clean"

    out = decide_keep_change(apply_fn=apply, revert_fn=revert, runner=_run(False))
    assert out["kept"] is False
    assert out["reverted"] is True
    assert state["value"] == "clean"
    assert out["log_line"].startswith(f"{GATE_NAME}: NO")


def test_decide_keep_keeps_good_change():
    state = {"value": "clean"}

    def apply():
        state["value"] = "good"

    def revert():
        state["value"] = "reverted"

    out = decide_keep_change(apply_fn=apply, revert_fn=revert, runner=_run(True))
    assert out["kept"] is True
    assert out["reverted"] is False
    assert state["value"] == "good"
    assert out["log_line"].startswith(f"{GATE_NAME}: YES")


def test_log_line_format():
    assert format_gate_log_line(keep=True, passes=2) == f"{GATE_NAME}: YES  passes=2/2"
    assert format_gate_log_line(keep=False, passes=1, reason="x").startswith(f"{GATE_NAME}: NO")


def test_nightly_records_gate_no(monkeypatch, tmp_path):
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "nightly_improvement_tests",
        Path(__file__).resolve().parents[1] / "scripts" / "nightly_improvement_tests.py",
    )
    nightly = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(nightly)
    monkeypatch.setattr(nightly, "LOG_DIR", tmp_path)
    monkeypatch.setattr(
        nightly,
        "_run",
        lambda cmd, cwd, env, timeout: {"cmd": cmd, "returncode": 0, "ok": True, "output": "ok"},
    )
    monkeypatch.setattr(
        nightly,
        "_run_frozen_gate",
        lambda env: {
            "keep": False,
            "verdict": "NO",
            "log_line": "STUDIO_FROZEN_GATE: NO  passes=0/2  mocked reject",
            "passes": 0,
            "required_passes": 2,
            "runs": [{"ok": False, "output": "FAILED frozen"}],
        },
    )
    res = nightly.run_nightly(dry_run=True)
    assert res["ok"] is False
    assert res["frozen_gate"]["verdict"] == "NO"
    assert res["frozen_gate"]["log_line"].startswith("STUDIO_FROZEN_GATE: NO")
    assert res["outbound"] is False
