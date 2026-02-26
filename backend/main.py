from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Empire API", version="2.5")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    from transcribe import router as transcribe_router
    app.include_router(transcribe_router, prefix="/api")
    print("✅ Transcription API loaded")
except Exception as e:
    print(f"⚠️ Transcription not loaded: {e}")

@app.get("/")
def root():
    return {"status": "Empire API v2.5", "audio": True}

@app.get("/health")
def health():
    return {"status": "ok"}
