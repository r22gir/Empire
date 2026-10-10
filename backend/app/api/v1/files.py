import os
import json
import shutil
import io
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from PIL import Image

router = APIRouter(prefix="/files", tags=["files"])

# Founder/Workroom legacy paths. Family editions never mkdir these.
UPLOAD_DIR = Path.home() / "empire-repo" / "backend" / "data" / "uploads"
LOG_DIR = Path.home() / "empire-repo" / "backend" / "data" / "logs" / "file_access"


def _upload_dir() -> Path:
    try:
        from app.edition import is_family_edition, require_data_root

        if is_family_edition():
            path = require_data_root() / "uploads"
            for cat in ['documents', 'code', 'images', 'audio', 'other']:
                (path / cat).mkdir(parents=True, exist_ok=True)
            return path
    except Exception:
        pass
    for cat in ['documents', 'code', 'images', 'audio', 'other']:
        (UPLOAD_DIR / cat).mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR


def _log_dir() -> Path:
    try:
        from app.edition import is_family_edition, require_data_root

        if is_family_edition():
            path = require_data_root() / "logs" / "file_access"
            path.mkdir(parents=True, exist_ok=True)
            return path
    except Exception:
        pass
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR

def get_category(filename: str) -> str:
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    if ext in ['pdf', 'txt', 'md', 'doc', 'docx', 'csv', 'json']:
        return 'documents'
    elif ext in ['py', 'js', 'ts', 'tsx', 'jsx', 'html', 'css', 'sh', 'yaml', 'yml']:
        return 'code'
    elif ext in ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico']:
        return 'images'
    elif ext in ['m4a', 'mp3', 'wav', 'ogg', 'flac', 'wma', 'aac']:
        return 'audio'
    return 'other'

def log_access(action: str, filename: str, agent: str, details: str = ""):
    log_entry = {"timestamp": datetime.now().isoformat(), "action": action, "filename": filename, "agent": agent, "details": details}
    log_file = _log_dir() / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"
    with open(log_file, 'a') as f:
        f.write(json.dumps(log_entry) + '\n')

class PathRequest(BaseModel):
    path: str

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "No filename")
    category = get_category(file.filename)
    save_path = _upload_dir() / category / file.filename
    if save_path.exists():
        stem, suffix = save_path.stem, save_path.suffix
        save_path = _upload_dir() / category / f"{stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{suffix}"
    raw_bytes = file.file.read()
    with open(save_path, 'wb') as f:
        f.write(raw_bytes)
    log_access("upload", file.filename, "founder", f"category={category}")

    # D44 — copy image-category uploads into the canonical job-images tree
    # so MAX can find them later via list_job_images / describe_job_image.
    # Email channel is intentionally NOT wired here (SendGrid retired 2026-08-27,
    # see D44 STEP 0 finding 3). Reuses decode_image_input from vision.py so
    # non-image payloads are rejected without writing a row.
    if category == "images":
        try:
            from app.services.job_image_store import store_job_image
            store_job_image(
                raw_bytes,
                source_channel="max_chat",
                original_filename=file.filename,
            )
        except ValueError as _ve:
            log_access("d44_reject", file.filename, "founder",
                       f"channel=max_chat reason={_ve}")

    return {"status": "success", "filename": save_path.name, "category": category, "size": save_path.stat().st_size}

@router.post("/upload-from-path")
async def upload_from_path(req: PathRequest):
    source = Path(req.path).expanduser()
    if not source.exists():
        raise HTTPException(404, "File not found")
    if not source.is_file():
        raise HTTPException(400, "Not a file")
    category = get_category(source.name)
    save_path = _upload_dir() / category / source.name
    if save_path.exists():
        save_path = _upload_dir() / category / f"{save_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{save_path.suffix}"
    shutil.copy2(source, save_path)
    log_access("upload", source.name, "founder", f"from={req.path}")
    return {"status": "success", "filename": save_path.name, "category": category, "size": save_path.stat().st_size}

@router.get("/browse")
async def browse_directory(path: str = "~"):
    try:
        from app.edition import is_family_edition, require_data_root, assert_under_root

        if is_family_edition():
            root = require_data_root()
            raw = (path or "").strip()
            target = root if not raw or raw in {"~", ".", "/"} else Path(raw)
            if not target.is_absolute():
                target = root / target
            target = assert_under_root(target, root)
            if not target.exists() or not target.is_dir():
                target = root
            files = []
            for f in sorted(target.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                if f.name.startswith('.'):
                    continue
                try:
                    files.append({
                        "name": f.name,
                        "path": str(f),
                        "isDir": f.is_dir(),
                        "size": f.stat().st_size if f.is_file() else 0
                    })
                except OSError:
                    pass
            return {"files": files, "current_path": str(target)}
    except Exception:
        from app.edition import is_family_edition, EditionPathError

        if is_family_edition():
            raise HTTPException(403, "Ruta fuera del directorio de esta instancia") from None
    target = Path(path).expanduser()
    if not target.exists():
        target = Path.home()
    if not target.is_dir():
        target = target.parent
    files = []
    try:
        for f in sorted(target.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if f.name.startswith('.'):
                continue
            try:
                files.append({
                    "name": f.name,
                    "path": str(f),
                    "isDir": f.is_dir(),
                    "size": f.stat().st_size if f.is_file() else 0
                })
            except:
                pass
    except PermissionError:
        pass
    return {"files": files, "current_path": str(target)}

@router.get("/list")
async def list_files(category: Optional[str] = None):
    files = []
    categories = [category] if category else ['documents', 'code', 'images', 'audio', 'other']
    for cat in categories:
        cat_path = _upload_dir() / cat
        if cat_path.exists():
            for f in cat_path.iterdir():
                if f.is_file():
                    files.append({"name": f.name, "category": cat, "size": f.stat().st_size, "uploaded_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat()})
    return {"files": files, "total": len(files)}

@router.get("/view/{category}/{filename}")
@router.get("/{category}/{filename}")
async def view_file(category: str, filename: str):
    # Prevent matching other named routes (list, logs, browse, upload, etc.)
    if category in ("list", "logs", "browse", "upload", "upload-from-path", "delete"):
        raise HTTPException(404, "File not found")
    file_path = _upload_dir() / category / filename
    if not file_path.exists():
        raise HTTPException(404, "File not found")
    log_access("view", filename, "founder", f"category={category}")
    return FileResponse(file_path)

@router.get("/logs")
async def get_logs(date: Optional[str] = None):
    target_date = date or datetime.now().strftime('%Y-%m-%d')
    log_file = _log_dir() / f"{target_date}.jsonl"
    if not log_file.exists():
        return {"logs": [], "date": target_date}
    logs = [json.loads(line) for line in open(log_file)]
    return {"logs": logs, "date": target_date}

@router.delete("/delete/{category}/{filename}")
async def delete_file(category: str, filename: str):
    file_path = _upload_dir() / category / filename
    if not file_path.exists():
        raise HTTPException(404, "File not found")
    file_path.unlink()
    log_access("delete", filename, "founder", f"category={category}")
    return {"status": "deleted", "filename": filename}
