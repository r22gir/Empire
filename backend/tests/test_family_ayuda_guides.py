"""Family /ayuda guides. Render-only. No WhatsApp sends, no Graph, no live data dirs."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

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


def test_whatsapp_guides_have_manito_sections_and_no_sends():
    for edition, host, other, must, must_not in (
        (
            "amp",
            "amp.empirebox.store",
            "maxine.empirebox.store",
            ("coaching", "Cibernettic", "formulario seguro", "¡Quiubo manito!"),
            ("Maxine", "Camilo", "Juan Diego", "lote 12"),
        ),
        (
            "maxine",
            "maxine.empirebox.store",
            "amp.empirebox.store",
            ("construcción", "inmuebles", "lote 12", "Juan ni de Rafael", "¡Quiubo manito!"),
            ("Max-e", "Camilo", "Juan Diego", "Cibernettic"),
        ),
    ):
        html = _render(WHATSAPP_SCRIPT, edition)
        assert f"https://{host}/api/v1/whatsapp/webhook" in html
        assert other not in html
        assert "WHATSAPP_ACCESS_TOKEN=" not in html
        assert "EAA" not in html
        assert "graph.facebook.com/v" not in html
        assert "3174437313" not in html
        assert "3122842350" not in html
        assert "Nunca escribe a clientes" in html or "nunca escribe a clientes" in html
        assert 'id="wa-0"' in html and 'id="wa-9"' in html
        assert "<figcaption>" in html
        assert "token permanente" in html
        assert "24" in html
        assert "plantillas" in html.lower()
        assert "número real" in html.lower() or "numero real" in html.lower()
        assert "solicitud segura" in html
        assert "formulario seguro" in html
        for needle in must:
            assert needle in html, needle
        for needle in must_not:
            assert needle not in html, needle


def test_empresa_and_device_guides_open_with_manito():
    for edition, host, other, must in (
        ("amp", "amp.empirebox.store", "maxine.empirebox.store", ("/amp/dashboard", "/amp/empresas", "Cibernettic")),
        ("maxine", "maxine.empirebox.store", "amp.empirebox.store", ("Portafolio", "Lotes", "construcción")),
    ):
        empresa = _render(EMPRESA_SCRIPT, edition)
        device = _render(DEVICE_SCRIPT, edition)
        assert "¡Quiubo manito!" in empresa
        assert "¡Quiubo manito!" in device
        assert host in empresa
        assert other not in empresa
        assert other not in device
        for needle in must:
            assert needle in empresa, needle
        assert "<figcaption>" in empresa
        assert "graph.facebook.com" not in empresa


def test_static_ayuda_pages_open_with_manito():
    menu = (ROOT / "empire-command-center" / "app" / "ayuda" / "page.tsx").read_text(encoding="utf-8")
    voz = (ROOT / "empire-command-center" / "app" / "ayuda" / "voz" / "page.tsx").read_text(encoding="utf-8")
    help_menu = (ROOT / "empire-command-center" / "app" / "components" / "voice" / "HelpMenu.tsx").read_text(encoding="utf-8")
    empresa_page = (ROOT / "empire-command-center" / "app" / "ayuda" / "empresa" / "page.tsx").read_text(encoding="utf-8")
    for text in (menu, voz):
        assert "AYUDA_OPENER" in text or "¡Quiubo manito!" in text
    assert "/ayuda/empresa" in menu
    assert "/ayuda/empresa" in help_menu
    assert "renderEmpresaGuidePage" in empresa_page
