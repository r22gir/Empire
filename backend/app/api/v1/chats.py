from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import json
import os
from pathlib import Path
from datetime import datetime
import uuid

router = APIRouter(prefix="/chats", tags=["chats"])

CHATS_DIR = Path(__file__).parent.parent.parent.parent / "data" / "chats"
CHATS_DIR.mkdir(parents=True, exist_ok=True)

class SaveChatRequest(BaseModel):
    user_id: str = "founder"
    messages: List[Dict]
    title: Optional[str] = None

class UpdateChatRequest(BaseModel):
    messages: List[Dict]

@router.post("/save")
async def save_chat(req: SaveChatRequest):
    chat_id = str(uuid.uuid4())[:8]
    title = req.title or f"Chat {datetime.now().strftime('%m/%d %H:%M')}"
    
    user_dir = CHATS_DIR / req.user_id
    user_dir.mkdir(exist_ok=True)
    
    chat_data = {
        "id": chat_id,
        "title": title,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "messages": req.messages,
    }
    
    with open(user_dir / f"{chat_id}.json", 'w') as f:
        json.dump(chat_data, f, indent=2)
    
    return {"status": "saved", "chat_id": chat_id, "title": title}

@router.put("/{chat_id}")
async def update_chat(chat_id: str, req: UpdateChatRequest, user_id: str = "founder"):
    chat_file = CHATS_DIR / user_id / f"{chat_id}.json"
    if not chat_file.exists():
        raise HTTPException(status_code=404, detail="Chat not found")
    
    with open(chat_file, 'r') as f:
        chat_data = json.load(f)
    
    chat_data["messages"] = req.messages
    chat_data["updated_at"] = datetime.now().isoformat()
    
    with open(chat_file, 'w') as f:
        json.dump(chat_data, f, indent=2)
    
    return {"status": "updated", "chat_id": chat_id}

@router.get("/list")
async def list_chats(user_id: str = "founder"):
    user_dir = CHATS_DIR / user_id
    if not user_dir.exists():
        return {"chats": [], "count": 0}
    
    chats = []
    for f in user_dir.glob("*.json"):
        with open(f, 'r') as file:
            data = json.load(file)
            chats.append({
                "id": data["id"],
                "title": data["title"],
                "updated_at": data["updated_at"],
                "message_count": len(data.get("messages", []))
            })
    
    chats.sort(key=lambda x: x["updated_at"], reverse=True)
    return {"chats": chats, "count": len(chats)}

@router.get("/{chat_id}")
async def load_chat(chat_id: str, user_id: str = "founder"):
    chat_file = CHATS_DIR / user_id / f"{chat_id}.json"
    if not chat_file.exists():
        raise HTTPException(status_code=404, detail="Chat not found")
    
    with open(chat_file, 'r') as f:
        return json.load(f)

class RenameChatRequest(BaseModel):
    title: str

@router.patch("/{chat_id}/title")
async def rename_chat(chat_id: str, req: RenameChatRequest, user_id: str = "founder"):
    chat_file = CHATS_DIR / user_id / f"{chat_id}.json"
    if not chat_file.exists():
        raise HTTPException(status_code=404, detail="Chat not found")
    with open(chat_file, 'r') as f:
        chat_data = json.load(f)
    chat_data["title"] = req.title
    chat_data["updated_at"] = datetime.now().isoformat()
    with open(chat_file, 'w') as f:
        json.dump(chat_data, f, indent=2)
    return {"status": "renamed", "title": req.title}

@router.delete("/{chat_id}")
async def delete_chat(chat_id: str, user_id: str = "founder"):
    chat_file = CHATS_DIR / user_id / f"{chat_id}.json"
    if chat_file.exists():
        os.remove(chat_file)
    return {"status": "deleted"}
