"""The device-access help route renders one edition at a time."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "empire-command-center" / "app" / "ayuda" / "dispositivos" / "page.tsx"
MENU = ROOT / "empire-command-center" / "app" / "ayuda" / "page.tsx"
HELP_MENU = ROOT / "empire-command-center" / "app" / "components" / "voice" / "HelpMenu.tsx"
WIZARD = ROOT / "empire-command-center" / "app" / "amp" / "empresas" / "entrevista" / "page.tsx"
NAV = ROOT / "empire-command-center" / "app" / "components" / "layout" / "LeftNav.tsx"


def _render(edition: str) -> str:
    script = """
import { renderDeviceAccessPage } from './empire-command-center/app/lib/deviceAccess.mjs';
process.stdout.write(renderDeviceAccessPage(process.env.EDITION || ''));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "EDITION": edition},
    )
    return result.stdout


def test_route_renders_only_the_signed_in_edition():
    max_e = _render("amp")
    maxine = _render("maxine")
    assert "Cómo conectarte desde tus dispositivos" in max_e
    assert "Sitio web (recomendado)" in max_e
    assert "https://amp.empirebox.store" in max_e
    assert "Agregar a pantalla de inicio" in max_e
    assert "Agregar a pantalla principal" in max_e
    assert "Tailscale" in max_e
    assert "WhatsApp, pronto" in max_e
    assert "maxine.empirebox.store" not in max_e
    assert "Maxine" not in max_e

    assert "https://maxine.empirebox.store" in maxine
    assert "Maxine" in maxine
    assert "amp.empirebox.store" not in maxine
    assert "Max-e" not in maxine
    assert "Live Voice" in maxine
    assert "correo que tienes autorizado" in maxine

    blank = _render("workroom")
    assert "Cómo conectarte desde tus dispositivos" in blank
    assert "amp.empirebox.store" not in blank
    assert "maxine.empirebox.store" not in blank

    page = PAGE.read_text(encoding="utf-8")
    assert "renderDeviceAccessPage" in page
    assert "useEdition" in page
    menu = MENU.read_text(encoding="utf-8")
    card = HELP_MENU.read_text(encoding="utf-8")
    wizard = WIZARD.read_text(encoding="utf-8")
    nav = NAV.read_text(encoding="utf-8")
    for text in (menu, card, nav):
        assert "/ayuda/dispositivos" in text or "/ayuda" in text
    assert "/ayuda/dispositivos" in menu
    assert "/ayuda/dispositivos" in card
    last = wizard.split("step === 9", 1)[1]
    assert 'href="/ayuda/dispositivos"' in last.split("step ===", 1)[0]
    assert "window.location.href = '/ayuda'" in nav
