from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import tempfile
import os

from app.services.max.stt_service import stt_service

router = APIRouter()


@router.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    if not stt_service.is_configured:
        raise HTTPException(status_code=503, detail="STT not configured — set GROQ_API_KEY")

    contents = await audio.read()
    if len(contents) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 25MB)")

    suffix = os.path.splitext(audio.filename or ".webm")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        text = await stt_service.transcribe(tmp_path)
        if text.startswith("["):
            raise HTTPException(status_code=500, detail=text)
        return JSONResponse({"success": True, "text": text})
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.get("/transcribe/status")
async def status():
    return {"available": stt_service.is_configured, "provider": "groq-whisper-large-v3-turbo"}
