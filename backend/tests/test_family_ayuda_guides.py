"""Family /ayuda guides. Render-only. No WhatsApp sends, no Graph, no live data dirs."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HANDOFF = (
    "Las llaves no van en el chat. "
    "Cuando las tengas, pégalas abajo en la pantalla segura. El token no se vuelve a mostrar."
)

WHATSAPP_SCRIPT = """
import { renderWhatsAppSetupPage } from './empire-command-center/app/lib/whatsappSetup.mjs';
process.stdout.write(renderWhatsAppSetupPage(process.env.EDITION || 'amp'));
"""

EMPRESA_SCRIPT = """
import { renderEmpresaGuidePage } from './empire-command-center/app/lib/empresaGuide.mjs';
process.stdout.write(renderEmpresaGuidePage(process.env.EDITION || 'amp'));
"""

DEVICE_SCRIPT = """
import { renderDeviceAccessPage } from './empire-command-center/app/lib/deviceAccess.mjs';
process.stdout.write(renderDeviceAccessPage(process.env.EDITION || 'amp'));
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


def test_whatsapp_guide_is_maxe_handoff_not_a_form():
    html = _render(WHATSAPP_SCRIPT, "amp")
    assert "¡Quiubo manito!" in html
    assert HANDOFF in html
    assert "Entrega de las llaves" in html
    assert "formulario seguro" not in html
    assert "solicitud segura" not in html
    assert "/home/rg/" not in html
    assert "8011" not in html
    assert "8012" not in html
    assert "https://amp.empirebox.store/api/v1/whatsapp/webhook" in html
    assert "maxine.empirebox.store" not in html
    assert "Maxine" not in html
    assert "Juan Diego" not in html
    assert "Conectar con clientes por WhatsApp" in html
    assert "Business Settings → System users" in html
    assert "whatsapp_business_messaging" in html
    assert "App settings → Basic" in html
    assert "Nunca escribe a clientes" in html
    assert 'id="wa-0"' in html and 'id="wa-9"' in html
    edition_src = (ROOT / "empire-command-center" / "app" / "lib" / "familyEdition.mjs").read_text(encoding="utf-8")
    assert "id: 'amp'" in edition_src
    assert "Juan Diego" not in edition_src
    assert "empire-amp.env" not in edition_src
    assert "Maxine" not in edition_src


def test_empresa_and_device_guides_open_with_manito():
    empresa = _render(EMPRESA_SCRIPT, "amp")
    device = _render(DEVICE_SCRIPT, "amp")
    assert "¡Quiubo manito!" in empresa
    assert "¡Quiubo manito!" in device
    assert "amp.empirebox.store" in empresa
    assert "maxine.empirebox.store" not in empresa
    assert "/amp/dashboard" in empresa
    assert "/ayuda/whatsapp" in device
    assert device.count("whatsapp") >= 1


def test_static_ayuda_pages_open_with_manito():
    menu = (ROOT / "empire-command-center" / "app" / "ayuda" / "page.tsx").read_text(encoding="utf-8")
    voz = (ROOT / "empire-command-center" / "app" / "ayuda" / "voz" / "page.tsx").read_text(encoding="utf-8")
    help_menu = (ROOT / "empire-command-center" / "app" / "components" / "voice" / "HelpMenu.tsx").read_text(encoding="utf-8")
    for text in (menu, voz):
        assert "AYUDA_OPENER" in text or "¡Quiubo manito!" in text
    assert "/ayuda/empresa" in menu
    assert "/ayuda/whatsapp" in help_menu
    assert help_menu.count("whatsapp") == 1
    if "Max-e arma cotizaciones" in voz:
        assert "Maxine" not in voz
