"""#131 safe deletions only — no calendar→Tasks routing."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_tracked_max_backups_are_gone():
    max_dir = REPO / "backend" / "app" / "services" / "max"
    leftovers = list(max_dir.glob("*.bak*"))
    assert leftovers == []


def test_unused_relist_screen_is_gone():
    assert not (REPO / "empire-command-center" / "app" / "components" / "screens" / "RelistAppScreen.tsx").exists()
    assert (REPO / "empire-command-center" / "app" / "components" / "screens" / "RelistAppPage.tsx").exists()


def test_leadforge_page_is_reexport_of_newer_page():
    text = (REPO / "empire-command-center" / "app" / "components" / "screens" / "LeadForgePage.tsx").read_text()
    assert "LeadForgePageNew" in text
    assert "export { default }" in text


def test_calendar_still_opens_organizer_not_tasks():
    app = (REPO / "empire-command-center" / "app" / "CommandCenterApp.tsx").read_text()
    assert "activeScreen === 'calendar'" in app
    assert "WorkroomOrganizer" in app
    nav = (REPO / "empire-command-center" / "app" / "components" / "layout" / "LeftNav.tsx").read_text()
    assert "screen: 'calendar'" in nav
    assert "name: 'Organizer'" in nav
