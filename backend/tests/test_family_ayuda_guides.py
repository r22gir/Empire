"""Family /ayuda guides. Render-only. No WhatsApp sends, no Graph, no live data dirs."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HANDOFF = (
    "Las llaves no van en el chat ni en esta página. "
    "Cuando las tengas, avísale a Rafael y él te dice cómo entregárselas de forma segura."
)
FORGE = ROOT / "empire-command-center" / "app" / "components" / "screens" / "ConstructionForgePage.tsx"

WHATSAPP_SCRIPT = """
import { renderWhatsAppSetupPage } from './empire-command-center/app/lib/whatsappSetup.mjs';
process.stdout.write(renderWhatsAppSetupPage(process.env.EDITION || 'maxine'));
"""

EMPRESA_SCRIPT = """
import { renderEmpresaGuidePage } from './empire-command-center/app/lib/empresaGuide.mjs';
process.stdout.write(renderEmpresaGuidePage(process.env.EDITION || 'maxine'));
"""

DEVICE_SCRIPT = """
import { renderDeviceAccessPage } from './empire-command-center/app/lib/deviceAccess.mjs';
process.stdout.write(renderDeviceAccessPage(process.env.EDITION || 'maxine'));
"""


def _render(script: str, edition: str) -> str:
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "EDITION": edition},
    )
    return result.stdout


def test_whatsapp_guide_is_maxine_handoff_not_a_form():
    html = _render(WHATSAPP_SCRIPT, "maxine")
    assert "¡Quiubo manito!" in html
    assert HANDOFF in html
    assert "Entrega de las llaves" in html
    assert "No reutilices llaves ni números de otra instancia." in html
    assert "formulario seguro" not in html
    assert "/home/rg/" not in html
    assert "8011" not in html
    assert "8012" not in html
    assert "https://maxine.empirebox.store/api/v1/whatsapp/webhook" in html
    assert "/whatsapp/chats" in html
    assert "/amp/" not in html
    assert "Max-e" not in html
    assert "Juan" not in html
    assert "Conectar con clientes por WhatsApp" in html
    edition_src = (ROOT / "empire-command-center" / "app" / "lib" / "familyEdition.mjs").read_text(encoding="utf-8")
    assert "id: 'maxine'" in edition_src
    assert "Juan Diego" not in edition_src
    assert "empire-amp.env" not in edition_src
    assert "8011" not in edition_src
    assert "Max-e" not in edition_src


def test_empresa_links_match_construction_screens():
    empresa = _render(EMPRESA_SCRIPT, "maxine")
    device = _render(DEVICE_SCRIPT, "maxine")
    forge = FORGE.read_text(encoding="utf-8")
    assert "¡Quiubo manito!" in empresa
    assert "/?product=construction&amp;section=lotmap" in empresa
    assert "/?product=construction&amp;section=buyers" in empresa
    assert "/?product=construction&amp;section=payments" in empresa
    assert "/amp/" not in empresa
    assert "id: 'lotmap'" in forge
    assert "case 'buyers'" in forge
    assert "case 'payments'" in forge
    assert "/ayuda/whatsapp" in device
    assert "/amp/" not in device


def test_static_ayuda_pages_open_with_manito():
    menu = (ROOT / "empire-command-center" / "app" / "ayuda" / "page.tsx").read_text(encoding="utf-8")
    voz = (ROOT / "empire-command-center" / "app" / "ayuda" / "voz" / "page.tsx").read_text(encoding="utf-8")
    help_menu = (ROOT / "empire-command-center" / "app" / "components" / "voice" / "HelpMenu.tsx").read_text(encoding="utf-8")
    chats = (ROOT / "empire-command-center" / "app" / "whatsapp" / "chats" / "page.tsx").read_text(encoding="utf-8")
    assert "AYUDA_OPENER" in menu
    assert "Maxine" in voz
    assert "Max-e" not in voz
    assert help_menu.count("whatsapp") == 1
    assert "/amp/whatsapp" not in help_menu
    assert "/whatsapp/chats" in chats
    assert "AmpNav" not in chats
