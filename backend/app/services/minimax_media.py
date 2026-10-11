"""MiniMax image-01 and speech-2.8 calls that always go through the meter."""
from __future__ import annotations

from typing import Any, Optional

from app.services.minimax_meter import (
    bilingual,
    current_edition,
    family_tts_enabled,
    is_family,
    pop_plan_warning,
    reconcile,
    reserve,
)
from app.services.minimax_prompts import PromptRejected, family_blocks_reference_image, sanitize_prompt


async def generate_image(
    prompt: str,
    *,
    aspect_ratio: str = "1:1",
    n: int = 1,
    edition: Optional[str] = None,
) -> dict[str, Any]:
    ed = edition or current_edition()
    try:
        cleaned = sanitize_prompt(prompt, edition=ed)
    except PromptRejected as exc:
        return {
            "success": False,
            "blocked": True,
            "error": bilingual(
                f"El aviso no se puede usar: {exc}. No se envían fotos ni datos de clientes.",
                f"Prompt rejected: {exc}. Client photos and data are not sent.",
            ),
        }
    count = max(1, min(int(n or 1), 1 if is_family(ed) else 4))
    reservation = reserve(kind="image", edition=ed, model="image-01", images=count)
    if reservation.blocked:
        return {"success": False, "blocked": True, "error": reservation.message}
    from app.services.max.minimax_tools import minimax_text_to_image

    try:
        result = await minimax_text_to_image(
            prompt=cleaned,
            aspect_ratio=aspect_ratio or "1:1",
            n=count,
            prompt_optimizer=True,
            model="image-01",
        )
    except Exception as exc:
        reconcile(reservation, billed_unknown=True, images=count, error=str(exc)[:200])
        return {"success": False, "blocked": False, "error": str(exc)[:200]}
    ok = bool(result.get("success"))
    made = int((result.get("data") or {}).get("count") or 0) if ok else 0
    if ok:
        reconcile(reservation, images=made or count)
        data = dict(result.get("data") or {})
        data["ai_generated"] = True
        data["label_es"] = "Imagen generada por IA (MiniMax image-01)."
        data["label_en"] = "AI-generated image (MiniMax image-01)."
        warning = reservation.warning or pop_plan_warning()
        if warning:
            data["warning"] = warning
        result["data"] = data
    else:
        reconcile(
            reservation,
            billed_unknown=True,
            images=count,
            error=str(result.get("error") or "")[:200],
        )
    return result


async def generate_speech(
    text: str,
    *,
    edition: Optional[str] = None,
    language: Optional[str] = None,
) -> dict[str, Any]:
    ed = edition or current_edition()
    if is_family(ed) and not family_tts_enabled():
        msg = bilingual(
            "La voz MiniMax (speech-2.8) está apagada en esta edición.",
            "MiniMax speech-2.8 voice is off for this edition.",
        )
        return {"success": False, "blocked": True, "error": msg}
    clean = (text or "").strip()
    reservation = reserve(
        kind="tts",
        edition=ed,
        model="speech-2.8-turbo",
        tts_chars=len(clean),
        tts_replies=1,
    )
    if reservation.blocked:
        return {"success": False, "blocked": True, "error": reservation.message}
    from app.services.max.minimax_tools import minimax_tts

    voice = "Spanish_Persuasive_Lady" if (language or "").startswith("es") or is_family(ed) else ""
    try:
        result = await minimax_tts(
            text=clean,
            voice_id=voice or "English_Persuasive_Man",
            speed=1.0,
            output_format="mp3",
        )
    except Exception as exc:
        reconcile(reservation, billed_unknown=True, tts_chars=len(clean), error=str(exc)[:200])
        return {"success": False, "blocked": False, "error": str(exc)[:200]}
    ok = bool(result.get("success"))
    if ok:
        reconcile(reservation, tts_chars=len(clean))
    else:
        reconcile(
            reservation,
            billed_unknown=True,
            tts_chars=len(clean),
            error=str(result.get("error") or "")[:200],
        )
    return result


def reject_family_image_to_image() -> Optional[str]:
    if family_blocks_reference_image():
        return bilingual(
            "Max-e y Maxine no envían fotos de clientes ni del Workroom a MiniMax.",
            "Max-e and Maxine do not send client or Workroom photos to MiniMax.",
        )
    return None
