"""Contract: Max Live transcript overlay defaults stay off the avatar face."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OVERLAY_TS = ROOT / "empire-command-center" / "app" / "lib" / "transcriptOverlay.ts"


def test_default_dock_in_frontend_lib_is_bottom():
    text = OVERLAY_TS.read_text(encoding="utf-8")
    assert "export const DEFAULT_TRANSCRIPT_OVERLAY" in text
    assert "dock: 'bottom'" in text
    assert "coversAvatarFace" in text
    assert "return dock === 'top'" in text
