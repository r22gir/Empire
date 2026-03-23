"""
Chat Backup API routes for managing chat sessions, backups, and decision context.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
import tempfile
import os

from app.database import get_async_db as get_db
from app.services.chat_backup_service import ChatBackupService
from app.services.context_unification_service import ContextUnificationService
from app.schemas.chat_backup import (
    # Session schemas
    ChatSessionCreate, ChatSessionUpdate, ChatSessionResponse, ChatSessionWithMessages,
    # Message schemas
    ChatMessageCreate, ChatMessageResponse,
    # Import/Export schemas
    ChatImportRequest, ChatExportResponse, BulkImportRequest, BulkImportResponse,
    # Backup schemas
    BackupRequest, BackupResponse, BackupStatus,
    # Context schemas
    DecisionContextCreate, DecisionContextUpdate, DecisionContextResponse,
    UnifyContextRequest, UnifiedContextResponse,
    # Disruption schemas
    DisruptionEventCreate, DisruptionEventUpdate, DisruptionEventResponse,
    # Dashboard
    ChatBackupDashboard
)

router = APIRouter()


# ============ Chat Session Endpoints ============

@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: ChatSessionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new chat session."""
    service = ChatBackupService(db)
    session = await service.create_session(session_data)
    message_count = await service.get_session_message_count(session.id)
    
    return ChatSessionResponse(
        **{k: v for k, v in session.__dict__.items() if not k.startswith('_')},
        message_count=message_count
    )


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def get_sessions(
    source: Optional[str] = Query(None, description="Filter by source"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_archived: Optional[bool] = Query(None, description="Filter by archived status"),
    is_backed_up: Optional[bool] = Query(None, description="Filter by backup status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Get chat sessions with optional filters."""
    service = ChatBackupService(db)
    sessions = await service.get_sessions(
        source=source,
        is_active=is_active,
        is_archived=is_archived,
        is_backed_up=is_backed_up,
        limit=limit,
        offset=offset
    )
    
    result = []
    for session in sessions:
        message_count = await service.get_session_message_count(session.id)
        result.append(ChatSessionResponse(
            **{k: v for k, v in session.__dict__.items() if not k.startswith('_')},
            message_count=message_count
        ))
    return result


@router.get("/sessions/{session_id}", response_model=ChatSessionWithMessages)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific chat session with messages."""
    service = ChatBackupService(db)
    session = await service.get_session(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    messages = await service.get_session_messages(session_id)
    message_responses = [
        ChatMessageResponse(**{k: v for k, v in msg.__dict__.items() if not k.startswith('_')})
        for msg in messages
    ]
    
    return ChatSessionWithMessages(
        **{k: v for k, v in session.__dict__.items() if not k.startswith('_')},
        message_count=len(messages),
        messages=message_responses
    )


@router.patch("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_session(
    session_id: UUID,
    update_data: ChatSessionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a chat session."""
    service = ChatBackupService(db)
    session = await service.update_session(session_id, update_data)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    message_count = await service.get_session_message_count(session.id)
    return ChatSessionResponse(
        **{k: v for k, v in session.__dict__.items() if not k.startswith('_')},
        message_count=message_count
    )


@router.post("/sessions/{session_id}/archive", response_model=ChatSessionResponse)
async def archive_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Archive a chat session."""
    service = ChatBackupService(db)
    session = await service.archive_session(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    message_count = await service.get_session_message_count(session.id)
    return ChatSessionResponse(
        **{k: v for k, v in session.__dict__.items() if not k.startswith('_')},
        message_count=message_count
    )


# ============ Chat Message Endpoints ============

@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def add_message(
    session_id: UUID,
    message_data: ChatMessageCreate,
    db: AsyncSession = Depends(get_db)
):
    """Add a message to a chat session."""
    service = ChatBackupService(db)
    message = await service.add_message(session_id, message_data)
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return ChatMessageResponse(**{k: v for k, v in message.__dict__.items() if not k.startswith('_')})


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_messages(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all messages for a chat session."""
    service = ChatBackupService(db)
    session = await service.get_session(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    messages = await service.get_session_messages(session_id)
    return [
        ChatMessageResponse(**{k: v for k, v in msg.__dict__.items() if not k.startswith('_')})
        for msg in messages
    ]


# ============ Import/Export Endpoints ============

@router.post("/import", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def import_chat(
    import_data: ChatImportRequest,
    db: AsyncSession = Depends(get_db)
):
    """Import a chat session from external source."""
    service = ChatBackupService(db)
    session = await service.import_chat(import_data)
    message_count = await service.get_session_message_count(session.id)
    
    return ChatSessionResponse(
        **{k: v for k, v in session.__dict__.items() if not k.startswith('_')},
        message_count=message_count
    )


@router.post("/import/bulk", response_model=BulkImportResponse, status_code=status.HTTP_201_CREATED)
async def bulk_import_chats(
    bulk_data: BulkImportRequest,
    db: AsyncSession = Depends(get_db)
):
    """Bulk import multiple chat sessions."""
    service = ChatBackupService(db)
    
    imported_ids = []
    errors = []
    
    for idx, session_data in enumerate(bulk_data.sessions):
        try:
            session = await service.import_chat(session_data)
            imported_ids.append(session.id)
        except Exception as e:
            errors.append({
                "index": idx,
                "title": session_data.title,
                "error": str(e)
            })
    
    return BulkImportResponse(
        imported_count=len(imported_ids),
        failed_count=len(errors),
        session_ids=imported_ids,
        errors=errors
    )


@router.post("/import/file", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def import_from_file(
    file: UploadFile = File(...),
    title: Optional[str] = Query(None, description="Optional title for the imported session"),
    db: AsyncSession = Depends(get_db)
):
    """Import a chat session from an uploaded file (JSON or text)."""
    service = ChatBackupService(db)
    
    # Save uploaded file temporarily
    suffix = ".json" if file.filename and file.filename.endswith(".json") else ".txt"
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        if suffix == ".json":
            session = await service.import_from_json_file(tmp_path)
        else:
            session = await service.import_from_text_file(tmp_path, title=title)
        
        message_count = await service.get_session_message_count(session.id)
        return ChatSessionResponse(
            **{k: v for k, v in session.__dict__.items() if not k.startswith('_')},
            message_count=message_count
        )
    finally:
        os.unlink(tmp_path)


@router.get("/sessions/{session_id}/export", response_model=ChatExportResponse)
async def export_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Export a chat session."""
    service = ChatBackupService(db)
    data = await service.export_session(session_id)
    
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    session = await service.get_session(session_id)
    messages = await service.get_session_messages(session_id)
    
    message_count = len(messages)
    return ChatExportResponse(
        session=ChatSessionResponse(
            **{k: v for k, v in session.__dict__.items() if not k.startswith('_')},
            message_count=message_count
        ),
        messages=[
            ChatMessageResponse(**{k: v for k, v in msg.__dict__.items() if not k.startswith('_')})
            for msg in messages
        ],
        exported_at=datetime.now(timezone.utc),
        export_format="json"
    )


# ============ Backup Endpoints ============

@router.post("/backup", response_model=BackupResponse)
async def backup_sessions(
    request: BackupRequest,
    db: AsyncSession = Depends(get_db)
):
    """Backup chat sessions to storage."""
    service = ChatBackupService(db)
    return await service.backup_sessions(request)


@router.get("/backup/status", response_model=BackupStatus)
async def get_backup_status(
    db: AsyncSession = Depends(get_db)
):
    """Get current backup status."""
    service = ChatBackupService(db)
    return await service.get_backup_status()


# ============ Decision Context Endpoints ============

@router.post("/contexts", response_model=DecisionContextResponse, status_code=status.HTTP_201_CREATED)
async def create_context(
    context_data: DecisionContextCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new decision context."""
    service = ContextUnificationService(db)
    context = await service.create_context(context_data)
    return DecisionContextResponse(**{k: v for k, v in context.__dict__.items() if not k.startswith('_')})


@router.get("/contexts", response_model=List[DecisionContextResponse])
async def get_contexts(
    category: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Get decision contexts with optional filters."""
    service = ContextUnificationService(db)
    contexts = await service.get_contexts(
        category=category,
        priority=priority,
        status=status,
        limit=limit,
        offset=offset
    )
    return [
        DecisionContextResponse(**{k: v for k, v in ctx.__dict__.items() if not k.startswith('_')})
        for ctx in contexts
    ]


@router.get("/contexts/active", response_model=List[DecisionContextResponse])
async def get_active_contexts(
    db: AsyncSession = Depends(get_db)
):
    """Get all active decision contexts."""
    service = ContextUnificationService(db)
    contexts = await service.get_active_contexts()
    return [
        DecisionContextResponse(**{k: v for k, v in ctx.__dict__.items() if not k.startswith('_')})
        for ctx in contexts
    ]


@router.get("/contexts/unified")
async def get_unified_context_for_agents(
    db: AsyncSession = Depends(get_db)
):
    """
    Get unified context for AI agents.
    Returns a combined context object suitable for agent decision-making.
    """
    service = ContextUnificationService(db)
    return await service.get_unified_context_for_agents()


@router.get("/contexts/{context_id}", response_model=DecisionContextResponse)
async def get_context(
    context_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific decision context."""
    service = ContextUnificationService(db)
    context = await service.get_context(context_id)
    
    if not context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Context not found"
        )
    
    return DecisionContextResponse(**{k: v for k, v in context.__dict__.items() if not k.startswith('_')})


@router.patch("/contexts/{context_id}", response_model=DecisionContextResponse)
async def update_context(
    context_id: UUID,
    update_data: DecisionContextUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a decision context."""
    service = ContextUnificationService(db)
    context = await service.update_context(context_id, update_data)
    
    if not context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Context not found"
        )
    
    return DecisionContextResponse(**{k: v for k, v in context.__dict__.items() if not k.startswith('_')})


@router.post("/contexts/{context_id}/archive", response_model=DecisionContextResponse)
async def archive_context(
    context_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Archive a decision context."""
    service = ContextUnificationService(db)
    context = await service.archive_context(context_id)
    
    if not context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Context not found"
        )
    
    return DecisionContextResponse(**{k: v for k, v in context.__dict__.items() if not k.startswith('_')})


# ============ Context Unification Endpoints ============

@router.post("/contexts/unify", response_model=UnifiedContextResponse, status_code=status.HTTP_201_CREATED)
async def unify_sessions(
    request: UnifyContextRequest,
    db: AsyncSession = Depends(get_db)
):
    """Unify multiple chat sessions into a decision context."""
    backup_service = ChatBackupService(db)
    unification_service = ContextUnificationService(db)
    
    try:
        context = await unification_service.unify_sessions(
            session_ids=request.session_ids,
            title=request.title,
            category=request.category,
            priority=request.priority.value if hasattr(request.priority, 'value') else request.priority,
            include_action_items=request.include_action_items
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Get source sessions for response
    source_sessions = []
    for sid in request.session_ids:
        session = await backup_service.get_session(sid)
        if session:
            message_count = await backup_service.get_session_message_count(sid)
            source_sessions.append(ChatSessionResponse(
                **{k: v for k, v in session.__dict__.items() if not k.startswith('_')},
                message_count=message_count
            ))
    
    return UnifiedContextResponse(
        context=DecisionContextResponse(**{k: v for k, v in context.__dict__.items() if not k.startswith('_')}),
        source_sessions=source_sessions,
        synthesis_notes=f"Unified {len(source_sessions)} sessions into context '{context.title}'"
    )


# ============ Disruption Event Endpoints ============

@router.post("/disruptions", response_model=DisruptionEventResponse, status_code=status.HTTP_201_CREATED)
async def log_disruption(
    event_data: DisruptionEventCreate,
    db: AsyncSession = Depends(get_db)
):
    """Log a disruption event."""
    service = ContextUnificationService(db)
    event = await service.log_disruption(event_data)
    return DisruptionEventResponse(**{k: v for k, v in event.__dict__.items() if not k.startswith('_')})


@router.get("/disruptions", response_model=List[DisruptionEventResponse])
async def get_recent_disruptions(
    limit: int = Query(10, ge=1, le=100),
    unresolved_only: bool = Query(False),
    db: AsyncSession = Depends(get_db)
):
    """Get recent disruption events."""
    service = ContextUnificationService(db)
    
    if unresolved_only:
        events = await service.get_unresolved_disruptions()
    else:
        events = await service.get_recent_disruptions(limit=limit)
    
    return [
        DisruptionEventResponse(**{k: v for k, v in event.__dict__.items() if not k.startswith('_')})
        for event in events
    ]


@router.get("/disruptions/{event_id}", response_model=DisruptionEventResponse)
async def get_disruption(
    event_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific disruption event."""
    service = ContextUnificationService(db)
    event = await service.get_disruption_event(event_id)
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Disruption event not found"
        )
    
    return DisruptionEventResponse(**{k: v for k, v in event.__dict__.items() if not k.startswith('_')})


@router.post("/disruptions/{event_id}/resolve", response_model=DisruptionEventResponse)
async def resolve_disruption(
    event_id: UUID,
    update_data: DisruptionEventUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Resolve a disruption event."""
    service = ContextUnificationService(db)
    event = await service.resolve_disruption(
        event_id=event_id,
        resolution_notes=update_data.resolution_notes
    )
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Disruption event not found"
        )
    
    return DisruptionEventResponse(**{k: v for k, v in event.__dict__.items() if not k.startswith('_')})


# ============ Dashboard Endpoint ============

@router.get("/dashboard", response_model=ChatBackupDashboard)
async def get_dashboard(
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard overview of chat backup system."""
    backup_service = ChatBackupService(db)
    unification_service = ContextUnificationService(db)
    
    # Get session counts
    all_sessions = await backup_service.get_sessions(limit=1000)
    active_sessions = [s for s in all_sessions if s.is_active]
    archived_sessions = [s for s in all_sessions if s.is_archived]
    
    # Get message count
    total_messages = await backup_service.get_message_count()
    
    # Get backup status
    backup_status = await backup_service.get_backup_status()
    
    # Get recent disruptions
    recent_disruptions = await unification_service.get_recent_disruptions(limit=5)
    
    # Get active context count
    active_contexts = await unification_service.get_context_count(status="active")
    
    return ChatBackupDashboard(
        total_sessions=len(all_sessions),
        active_sessions=len(active_sessions),
        archived_sessions=len(archived_sessions),
        total_messages=total_messages,
        backup_status=backup_status,
        recent_disruptions=[
            DisruptionEventResponse(**{k: v for k, v in event.__dict__.items() if not k.startswith('_')})
            for event in recent_disruptions
        ],
        active_contexts=active_contexts,
        last_unification_at=None  # Could be tracked separately
    )
