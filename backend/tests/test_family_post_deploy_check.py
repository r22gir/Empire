"""Post-deploy script: parse unquoted env values; prefer backend/venv python."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "deploy" / "family_post_deploy_check.sh"


def test_script_does_not_source_or_eval_env():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "set -a" not in text
    assert '. "$env_file"' not in text
    assert 'source "$env_file"' not in text
    assert "backend/venv/bin/python" in text
    assert "read_env_key" in text
    assert "mi empresa se llama" in text
    assert "POSTDEPLOY-" not in text
    assert "used_percent + remaining_percent debe igualar cap_percent" in text
    assert "check_family_help" in text
    assert "family-help /inbox denegado" in text
    assert "can_read_inbox" in text
    assert "check_minimax_meter" in text
    assert "minimax-meter /usage denegado" in text
    assert "minimax-meter /me" in text
    assert "check_legal_refusal" in text
    assert "datos legales ofreció guardar" in text
    assert "share the data" in text
    assert "información pública" in text or "informacion publica" in text
    assert "no comparto" in text


def test_self_test_parses_unquoted_smtp_from():
    out = subprocess.run(
        ["bash", str(SCRIPT), "--self-test"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert out.returncode == 0, out.stderr + out.stdout
    assert "self-test ok" in out.stdout
