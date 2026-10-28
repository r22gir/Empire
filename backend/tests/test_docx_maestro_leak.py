"""Max-e ticket fh-bec7a9e9f39e: MiniMax tool-call leak + DOCX fallback.

Juan's Centro de mando chat showed raw MiniMax protocol:

    ]<]minimax[>[<tool_call>
    to=functions.execute_code … Tool "execute_code" is not available

and then dead-ended because LibreOffice was missing.

No live model. No paid APIs. No real sends.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.routers.max.router import _sanitize_internal_leakage_text
from app.services.max.docx_maestro import (
    extractive_summary,
    format_user_reply,
    is_docx_process_ask,
    looks_like_docx_code_job,
    looks_like_plan_or_deadend,
    process_docx,
    unknown_tool_reply,
    verify_pagination,
)
from app.services.max.thinking import strip_protocol_delimiters, strip_thinking
from app.services.max.tool_executor import parse_tool_blocks, strip_tool_blocks

TICKET_LEAK = (
    "Esta vez voy a ejecutar el procesamiento real y no a describir un plan: "
    "buscaré el DOCX adjunto, revisaré su cuerpo completo, generaré el maestro "
    "y el resumen, y verificaré la paginación antes de publicar los enlaces.]"
    "<]minimax[>[<tool_call>\r\n]<]minimax[>[ LibreOffice no está disponible en "
    "este runtime, así que no puedo paginar ni calcular la tabla de contenido "
    "con el método previsto. El DOCX sí queda localizado, pero no voy a "
    "publicar un maestro sin esas comprobaciones.]<]minimax[>[<tool_call>\r\n"
    'to=functions.execute_code code errorType=unknown_error, error=Tool '
    '\\"execute_code\\" is not available in this environment.'
)

PROOF_DIR = Path(__file__).resolve().parents[2] / "reports"
PROOF_JSON = PROOF_DIR / "2026-10-28_maxe_docx_chat_path.json"
PROOF_LOG = PROOF_DIR / "2026-10-28_maxe_docx_realpath.txt"


def _sample_docx(path: Path) -> Path:
    import docx

    document = docx.Document()
    document.add_heading("Informe de prueba AMP", level=1)
    document.add_paragraph(
        "Este es el cuerpo completo del documento de Juan. "
        "Describe el plan de trabajo de la semana y los acuerdos del equipo."
    )
    document.add_heading("Objetivos", level=2)
    document.add_paragraph(
        "Cerrar el maestro y el resumen sin depender de LibreOffice. "
        "Publicar enlaces reales para el centro de mando."
    )
    document.add_heading("Notas", level=2)
    document.add_paragraph("La paginación exacta es opcional cuando no hay soffice.")
    path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(path))
    return path


def test_ticket_leak_tokens_are_stripped():
    cleaned = _sanitize_internal_leakage_text(TICKET_LEAK)
    assert "]<]minimax[>" not in cleaned
    assert "<tool_call>" not in cleaned
    assert "to=functions" not in cleaned
    assert "execute_code" not in cleaned
    assert "errorType" not in cleaned
    assert "unknown_error" not in cleaned
    assert "is not available in this environment" not in cleaned


def test_strip_thinking_keeps_spanish_and_drops_delimiters():
    cleaned = strip_thinking(TICKET_LEAK)
    assert "maestro" in cleaned.lower()
    assert "]<]minimax[>" not in cleaned
    assert strip_protocol_delimiters("hola]<]minimax[>[mundo") == "holamundo"


def test_minimax_execute_code_markup_is_parsed_and_stripped():
    calls = parse_tool_blocks(TICKET_LEAK)
    assert [c["tool"] for c in calls] == ["execute_code"]
    visible = strip_tool_blocks(TICKET_LEAK)
    assert "<tool_call>" not in visible
    assert "to=functions" not in visible
    assert "execute_code" not in visible
    assert "errorType" not in visible


def test_unknown_tool_error_is_short_spanish(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    from app.edition import apply_amp_process_paths
    from app.services.max.tool_executor import ToolResult, execute_tool

    apply_amp_process_paths()
    result = execute_tool({"tool": "execute_code", "code": "print(1)"}, founder=True)
    assert isinstance(result, ToolResult)
    assert result.success is False
    assert result.tool == "execute_code"
    assert result.error == unknown_tool_reply("execute_code")
    assert "is not available in this environment" not in (result.error or "")
    assert "Available tools:" not in (result.error or "")


def test_family_missing_tool_is_spanish(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    from app.edition import apply_amp_process_paths
    from app.services.max.tool_executor import execute_tool

    apply_amp_process_paths()
    result = execute_tool({"tool": "execute_code", "code": "print(1)"}, founder=True)
    assert result.success is False
    assert result.error == unknown_tool_reply("execute_code")
    assert "Available tools:" not in result.error


def test_execute_code_docx_job_redirects(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    from app.edition import apply_amp_process_paths
    from app.services.max.tool_executor import execute_tool

    apply_amp_process_paths()
    src = _sample_docx(tmp_path / "uploads" / "documents" / "plan.docx")
    assert looks_like_docx_code_job({"tool": "execute_code", "code": "import docx; maestro()"})
    result = execute_tool(
        {"tool": "execute_code", "code": f"read {src.name} and write maestro"},
        founder=True,
    )
    # Redirect only happens when the call looks like a DOCX job; filename may
    # still be missing, so success can be false with a Spanish file error.
    assert result.tool == "process_docx"


def test_docx_fallback_without_libreoffice(tmp_path, monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    from app.edition import apply_amp_process_paths

    apply_amp_process_paths()
    src = _sample_docx(tmp_path / "uploads" / "documents" / "informe_juan.docx")
    monkeypatch.setattr("app.services.max.docx_maestro.libreoffice_available", lambda: False)
    monkeypatch.setattr(
        "app.services.max.docx_maestro.shutil.which",
        lambda *_a, **_k: None,
    )
    pages = verify_pagination(src)
    assert pages["available"] is False
    assert pages["verified"] is False

    result = process_docx(src.name, path=str(src))
    assert result["ok"] is True
    assert result["pagination_verified"] is False
    assert result["libreoffice"] is False
    assert Path(result["maestro"]["path"]).is_file()
    assert Path(result["resumen"]["path"]).is_file()
    assert result["maestro"]["bytes"] > 0
    assert result["resumen"]["bytes"] > 0
    assert "/api/v1/files/view/documents/" in result["maestro"]["url"]
    assert "/api/v1/files/view/documents/" in result["resumen"]["url"]
    assert "LibreOffice" in result["user_reply"]
    assert "maestro" in result["user_reply"].lower()
    import docx

    master = docx.Document(result["maestro"]["path"])
    body = "\n".join(p.text for p in master.paragraphs)
    assert "cuerpo completo" in body.lower() or "Informe de prueba AMP" in body
    assert "Publicar enlaces reales" in body


def test_intent_and_plan_detectors():
    assert is_docx_process_ask(
        "Lee el DOCX, genera el maestro y el resumen, verifica paginación y publica enlaces",
        "informe.docx",
    )
    assert not is_docx_process_ask("hola manito", None)
    assert looks_like_plan_or_deadend(TICKET_LEAK)
    assert not looks_like_plan_or_deadend("Listo. Aquí están los enlaces del maestro.")


def test_extractive_summary_uses_headings():
    parts = ["Introducción larga del documento.", "Objetivos", "Cerrar el maestro."]
    outline = ["1. Objetivos"]
    summary = extractive_summary(parts, outline)
    assert "Objetivos" in summary


def _family_env(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.setenv("ASSISTANT_NAME", "Max-e")
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))
    monkeypatch.delenv("FOUNDER_PIN", raising=False)
    from app.edition import apply_amp_process_paths

    apply_amp_process_paths()


def _patch_chat_path(monkeypatch, fake_chat, fake_stream, fake_execute):
    import importlib

    from app.services.max.ai_router import ai_router

    max_router = importlib.import_module("app.routers.max.router")
    dummy = type("Handoff", (), {
        "is_drawing_intent": False,
        "ready": False,
        "missing": [],
        "intent_mode": "unknown",
    })()

    async def no_link(*_a, **_k):
        return None

    monkeypatch.setattr(max_router, "_is_family_edition", lambda: True)
    monkeypatch.setattr(max_router, "_family_pre_search_open", lambda _desk: False)
    monkeypatch.setattr(max_router, "_link_intelligence_response", no_link)
    monkeypatch.setattr(max_router, "_maybe_handle_direct_route_request", lambda *_a, **_k: None)
    monkeypatch.setattr(max_router, "_maybe_handle_gpu_safety_request", lambda *_a, **_k: None)
    monkeypatch.setattr(max_router, "should_run_whats_new_summary", lambda *_a, **_k: False)
    monkeypatch.setattr(max_router, "should_force_runtime_truth_check", lambda *_a, **_k: False)
    monkeypatch.setattr(max_router, "should_clarify_inventory_request", lambda *_a, **_k: False)
    monkeypatch.setattr(max_router, "build_drawing_handoff", lambda *_a, **_k: dummy)
    monkeypatch.setattr(max_router, "execute_tool", fake_execute)
    monkeypatch.setattr(ai_router, "chat", fake_chat)
    monkeypatch.setattr(ai_router, "chat_stream", fake_stream)
    try:
        from app.services.max import factual_guard
        monkeypatch.setattr(factual_guard, "is_factual_question", lambda *_a, **_k: False)
    except Exception:
        pass
    try:
        import app.services.max.continuity_compaction as continuity
        monkeypatch.setattr(continuity, "should_handle_continuity_command", lambda *_a, **_k: False)
        monkeypatch.setattr(continuity, "should_run_continuity_audit", lambda *_a, **_k: False)
    except Exception:
        pass
    return max_router


def test_chat_docx_path_strips_leak_and_delivers(monkeypatch, tmp_path):
    """POST /api/v1/max/chat — the door Juan's Command Center hits."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routers.max.router import router
    from app.services.max.ai_router import AIResponse
    from app.services.max.tool_executor import ToolResult

    _family_env(monkeypatch, tmp_path)
    src = _sample_docx(tmp_path / "uploads" / "documents" / "adjunto_juan.docx")
    executed: list[str] = []
    real = process_docx(src.name, path=str(src))
    assert real["ok"] is True

    async def fake_chat(*_a, **_k):
        return AIResponse(content=TICKET_LEAK, model_used="MiniMax-M3")

    async def fake_stream(*_a, **_k):
        yield TICKET_LEAK, "MiniMax-M3"
        return
        yield  # pragma: no cover

    def fake_execute(tool_call, *_a, **_k):
        tool = str((tool_call or {}).get("tool") or "")
        executed.append(tool)
        if tool == "process_docx":
            return ToolResult(tool="process_docx", success=True, result=real)
        if tool == "execute_code":
            return ToolResult(tool="execute_code", success=False, error=unknown_tool_reply(tool))
        return ToolResult(tool=tool or "unknown", success=False, error="unused")

    _patch_chat_path(monkeypatch, fake_chat, fake_stream, fake_execute)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)
    message = (
        "Procesa el DOCX adjunto: lee el cuerpo completo, genera el maestro "
        "y el resumen, verifica la paginación y publica los enlaces."
    )
    res = client.post(
        "/api/v1/max/chat",
        json={
            "message": message,
            "channel": "dashboard",
            "usage_source": "web",
            "image_filename": src.name,
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    text = body["response"]
    import shutil

    PROOF_DIR.mkdir(parents=True, exist_ok=True)
    saved_maestro = PROOF_DIR / real["maestro"]["filename"]
    saved_resumen = PROOF_DIR / real["resumen"]["filename"]
    shutil.copy2(real["maestro"]["path"], saved_maestro)
    shutil.copy2(real["resumen"]["path"], saved_resumen)
    PROOF_JSON.write_text(json.dumps({
        "endpoint": "/api/v1/max/chat",
        "ticket": "fh-bec7a9e9f39e",
        "user": message,
        "attachment": src.name,
        "model_payload": TICKET_LEAK,
        "executed_tools": executed,
        "process_docx": {
            "ok": real["ok"],
            "maestro": real["maestro"],
            "resumen": real["resumen"],
            "pagination": real["pagination"],
            "paragraph_count": real["paragraph_count"],
        },
        "response": body,
    }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    PROOF_LOG.write_text(
        "POST /api/v1/max/chat  (Max-e Centro de mando)\n"
        f"attachment={src.name}\n"
        f"executed={executed}\n"
        f"maestro={real['maestro']['path']}\n"
        f"resumen={real['resumen']['path']}\n"
        f"libreoffice={real['libreoffice']}\n"
        f"pagination_verified={real['pagination_verified']}\n\n"
        f"visible_reply=\n{text}\n",
        encoding="utf-8",
    )
    assert "process_docx" in executed
    assert "]<]minimax[>" not in text
    assert "<tool_call>" not in text
    assert "to=functions" not in text
    assert "execute_code" not in text
    assert "errorType" not in text
    assert "/files/view/documents/" in text
    assert "maestro" in text.lower()
    assert "resumen" in text.lower()
    assert "LibreOffice" in text


def test_family_graceful_reply_uses_docx_delivery(monkeypatch, tmp_path):
    import importlib

    _family_env(monkeypatch, tmp_path)
    max_router = importlib.import_module("app.routers.max.router")
    from app.routers.max.router import ChatRequest

    monkeypatch.setattr(max_router, "_is_family_edition", lambda: True)
    req = ChatRequest(
        message="Genera el maestro y el resumen del DOCX",
        image_filename="adjunto.docx",
    )
    delivery = format_user_reply(
        source_name="adjunto.docx",
        maestro_url="/api/v1/files/view/documents/a_maestro.docx",
        resumen_url="/api/v1/files/view/documents/a_resumen.docx",
        pagination={"verified": False, "pages": None},
        paragraph_count=4,
    )
    visible = max_router._family_graceful_visible_reply(
        TICKET_LEAK,
        req,
        [{"tool": "process_docx", "success": True, "result": {"user_reply": delivery}}],
    )
    assert visible == delivery
    assert "]<]minimax[>" not in visible
