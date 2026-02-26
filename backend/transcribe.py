from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import tempfile
import os

router = APIRouter()

# Intentar cargar Whisper
try:
    import whisper
    model = whisper.load_model("base")
    WHISPER_OK = True
    print("✅ Whisper cargado")
except:
    WHISPER_OK = False
    model = None
    print("⚠️ Whisper no disponible")

@router.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    if not WHISPER_OK:
        raise HTTPException(status_code=503, detail="Whisper no instalado")
    
    contents = await audio.read()
    if len(contents) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Archivo muy grande (max 25MB)")
    
    suffix = os.path.splitext(audio.filename or ".webm")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name
    
    try:
        result = model.transcribe(tmp_path, language="es", fp16=False)
        return JSONResponse({"success": True, "text": result["text"]})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@router.get("/transcribe/status")
async def status():
    return {"available": WHISPER_OK}
