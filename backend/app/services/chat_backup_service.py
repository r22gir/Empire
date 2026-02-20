"""
Chat Backup Service for managing chat sessions, backups, and imports.
Handles periodic backup, import/export, and storage operations.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.models.chat_backup import ChatSession, ChatMessage, DecisionContext, DisruptionEvent
from app.schemas.chat_backup import (
    ChatSessionCreate, ChatSessionUpdate, ChatMessageCreate,
    ChatImportRequest, BackupRequest, BackupResponse, BackupStatus,
    DecisionContextCreate, DecisionContextUpdate,
    DisruptionEventCreate, DisruptionEventUpdate
)


class ChatBackupService:
    """Service for chat backup operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.default_backup_dir = os.getenv("CHAT_BACKUP_DIR", "/tmp/chat_backups")

    # ============ Chat Session Operations ============

    async def create_session(self, session_data: ChatSessionCreate) -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(
            title=session_data.title,
            source=session_data.source.value if hasattr(session_data.source, 'value') else session_data.source,
            external_id=session_data.external_id,
            ai_model=session_data.ai_model,
            agent_name=session_data.agent_name,
            tags=session_data.tags,
            session_metadata=session_data.metadata,
            started_at=session_data.started_at or datetime.now(timezone.utc)
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session(self, session_id: UUID) -> Optional[ChatSession]:
        """Get a chat session by ID."""
        result = await self.db.execute(
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .where(ChatSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_sessions(
        self,
        source: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_archived: Optional[bool] = None,
        is_backed_up: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ChatSession]:
        """Get chat sessions with optional filters."""
        query = select(ChatSession)

        if source:
            query = query.where(ChatSession.source == source)
        if is_active is not None:
            query = query.where(ChatSession.is_active == is_active)
        if is_archived is not None:
            query = query.where(ChatSession.is_archived == is_archived)
        if is_backed_up is not None:
            query = query.where(ChatSession.is_backed_up == is_backed_up)

        query = query.order_by(ChatSession.started_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_session(self, session_id: UUID, update_data: ChatSessionUpdate) -> Optional[ChatSession]:
        """Update a chat session."""
        session = await self.get_session(session_id)
        if not session:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(session, key, value)

        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def archive_session(self, session_id: UUID) -> Optional[ChatSession]:
        """Archive a chat session."""
        session = await self.get_session(session_id)
        if not session:
            return None

        session.is_archived = True
        session.is_active = False
        session.ended_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(session)
        return session

    # ============ Chat Message Operations ============

    async def add_message(self, session_id: UUID, message_data: ChatMessageCreate) -> Optional[ChatMessage]:
        """Add a message to a chat session."""
        session = await self.get_session(session_id)
        if not session:
            return None

        message = ChatMessage(
            session_id=session_id,
            role=message_data.role.value if hasattr(message_data.role, 'value') else message_data.role,
            content=message_data.content,
            sequence_number=message_data.sequence_number,
            token_count=message_data.token_count,
            ai_model=message_data.ai_model,
            completion_tokens=message_data.completion_tokens,
            prompt_tokens=message_data.prompt_tokens,
            references=message_data.references,
            message_metadata=message_data.metadata
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def get_session_messages(self, session_id: UUID) -> List[ChatMessage]:
        """Get all messages for a session."""
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.sequence_number)
        )
        return list(result.scalars().all())

    # ============ Import Operations ============

    async def import_chat(self, import_data: ChatImportRequest) -> ChatSession:
        """Import a chat session from external source."""
        # Create the session
        session = ChatSession(
            title=import_data.title or f"Imported chat - {datetime.now(timezone.utc).isoformat()}",
            source=import_data.source.value if hasattr(import_data.source, 'value') else import_data.source,
            external_id=import_data.external_id,
            ai_model=import_data.ai_model,
            tags=import_data.tags,
            session_metadata=import_data.metadata,
            started_at=import_data.started_at or datetime.now(timezone.utc),
            ended_at=import_data.ended_at,
            is_active=False  # Imported sessions are not active
        )
        self.db.add(session)
        await self.db.flush()

        # Add messages
        for idx, msg in enumerate(import_data.messages):
            message = ChatMessage(
                session_id=session.id,
                role=msg.role.value if hasattr(msg.role, 'value') else msg.role,
                content=msg.content,
                sequence_number=idx + 1,
                message_metadata=msg.metadata,
                created_at=msg.timestamp or datetime.now(timezone.utc)
            )
            self.db.add(message)

        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def import_from_text_file(self, file_path: str, title: Optional[str] = None) -> ChatSession:
        """Import chat from a plain text file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse the content - simple format: alternating user/assistant messages
        # This is a basic parser; can be extended for more complex formats
        lines = content.strip().split('\n')
        messages = []
        current_role = "user"
        current_content = []

        from app.schemas.chat_backup import ChatImportMessage, MessageRoleEnum

        for line in lines:
            line = line.strip()
            if not line:
                if current_content:
                    messages.append(ChatImportMessage(
                        role=MessageRoleEnum(current_role),
                        content='\n'.join(current_content)
                    ))
                    current_content = []
                    current_role = "assistant" if current_role == "user" else "user"
            else:
                current_content.append(line)

        # Add last message if any
        if current_content:
            messages.append(ChatImportMessage(
                role=MessageRoleEnum(current_role),
                content='\n'.join(current_content)
            ))

        import_request = ChatImportRequest(
            title=title or os.path.basename(file_path),
            source="external_import",
            messages=messages,
            metadata={"source_file": file_path}
        )

        return await self.import_chat(import_request)

    async def import_from_json_file(self, file_path: str) -> ChatSession:
        """Import chat from a JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        from app.schemas.chat_backup import ChatImportMessage, MessageRoleEnum, ChatSourceEnum

        messages = []
        for msg in data.get('messages', []):
            messages.append(ChatImportMessage(
                role=MessageRoleEnum(msg.get('role', 'user')),
                content=msg.get('content', ''),
                timestamp=datetime.fromisoformat(msg['timestamp']) if msg.get('timestamp') else None,
                metadata=msg.get('metadata', {})
            ))

        import_request = ChatImportRequest(
            title=data.get('title', os.path.basename(file_path)),
            source=ChatSourceEnum(data.get('source', 'external_import')),
            external_id=data.get('external_id'),
            ai_model=data.get('ai_model'),
            messages=messages,
            started_at=datetime.fromisoformat(data['started_at']) if data.get('started_at') else None,
            ended_at=datetime.fromisoformat(data['ended_at']) if data.get('ended_at') else None,
            tags=data.get('tags', []),
            metadata=data.get('metadata', {})
        )

        return await self.import_chat(import_request)

    # ============ Export Operations ============

    async def export_session(self, session_id: UUID) -> Dict[str, Any]:
        """Export a chat session to a dictionary."""
        session = await self.get_session(session_id)
        if not session:
            return {}

        messages = await self.get_session_messages(session_id)

        return {
            "id": str(session.id),
            "title": session.title,
            "source": session.source,
            "external_id": session.external_id,
            "ai_model": session.ai_model,
            "agent_name": session.agent_name,
            "tags": session.tags,
            "metadata": session.session_metadata,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "sequence_number": msg.sequence_number,
                    "token_count": msg.token_count,
                    "ai_model": msg.ai_model,
                    "references": msg.references,
                    "metadata": msg.message_metadata,
                    "timestamp": msg.created_at.isoformat() if msg.created_at else None
                }
                for msg in messages
            ],
            "exported_at": datetime.now(timezone.utc).isoformat()
        }

    async def export_to_file(self, session_id: UUID, file_path: str) -> bool:
        """Export a chat session to a JSON file."""
        data = await self.export_session(session_id)
        if not data:
            return False

        os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return True

    # ============ Backup Operations ============

    async def backup_sessions(self, request: BackupRequest) -> BackupResponse:
        """Backup chat sessions to storage."""
        # Determine which sessions to backup
        if request.session_ids:
            sessions = []
            for sid in request.session_ids:
                session = await self.get_session(sid)
                if session:
                    sessions.append(session)
        else:
            query = select(ChatSession).where(ChatSession.is_backed_up == False)
            if not request.include_archived:
                query = query.where(ChatSession.is_archived == False)
            result = await self.db.execute(query)
            sessions = list(result.scalars().all())

        if not sessions:
            return BackupResponse(
                backup_id=str(uuid4()),
                sessions_backed_up=0,
                backup_location=request.backup_location or self.default_backup_dir,
                backup_size_bytes=0,
                backed_up_at=datetime.now(timezone.utc)
            )

        # Create backup directory
        backup_location = request.backup_location or self.default_backup_dir
        backup_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(backup_location, f"backup_{backup_timestamp}")
        os.makedirs(backup_dir, exist_ok=True)

        total_size = 0
        for session in sessions:
            file_path = os.path.join(backup_dir, f"session_{session.id}.json")
            await self.export_to_file(session.id, file_path)
            total_size += os.path.getsize(file_path)

            # Mark as backed up
            session.is_backed_up = True
            session.backup_location = file_path
            session.last_backup_at = datetime.now(timezone.utc)

        await self.db.commit()

        return BackupResponse(
            backup_id=backup_timestamp,
            sessions_backed_up=len(sessions),
            backup_location=backup_dir,
            backup_size_bytes=total_size,
            backed_up_at=datetime.now(timezone.utc)
        )

    async def get_backup_status(self) -> BackupStatus:
        """Get current backup status."""
        # Count sessions
        total_result = await self.db.execute(select(func.count(ChatSession.id)))
        total_sessions = total_result.scalar() or 0

        backed_up_result = await self.db.execute(
            select(func.count(ChatSession.id)).where(ChatSession.is_backed_up == True)
        )
        backed_up_sessions = backed_up_result.scalar() or 0

        # Get last backup time
        last_backup_result = await self.db.execute(
            select(func.max(ChatSession.last_backup_at))
        )
        last_backup_at = last_backup_result.scalar()

        # Calculate next scheduled backup (every 6 hours by default)
        backup_interval_hours = int(os.getenv("CHAT_BACKUP_INTERVAL_HOURS", "6"))
        next_scheduled = None
        if last_backup_at:
            next_scheduled = last_backup_at + timedelta(hours=backup_interval_hours)
        else:
            next_scheduled = datetime.now(timezone.utc) + timedelta(hours=backup_interval_hours)

        return BackupStatus(
            last_backup_at=last_backup_at,
            total_sessions=total_sessions,
            backed_up_sessions=backed_up_sessions,
            pending_sessions=total_sessions - backed_up_sessions,
            next_scheduled_backup=next_scheduled
        )

    # ============ Statistics ============

    async def get_session_count(self) -> int:
        """Get total number of sessions."""
        result = await self.db.execute(select(func.count(ChatSession.id)))
        return result.scalar() or 0

    async def get_message_count(self) -> int:
        """Get total number of messages."""
        result = await self.db.execute(select(func.count(ChatMessage.id)))
        return result.scalar() or 0

    async def get_session_message_count(self, session_id: UUID) -> int:
        """Get message count for a specific session."""
        result = await self.db.execute(
            select(func.count(ChatMessage.id)).where(ChatMessage.session_id == session_id)
        )
        return result.scalar() or 0
