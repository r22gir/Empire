"""
Chat Backup and Decision Context schemas for API requests and responses.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum


class ChatSourceEnum(str, Enum):
    """Source/origin of chat messages."""
    COPILOT = "copilot"
    AI_AGENT = "ai_agent"
    USER = "user"
    EXTERNAL_IMPORT = "external_import"
    SYSTEM = "system"


class MessageRoleEnum(str, Enum):
    """Role of the message sender."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class PriorityEnum(str, Enum):
    """Priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class ImpactLevelEnum(str, Enum):
    """Impact levels for disruption events."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ============ Chat Message Schemas ============

class ChatMessageCreate(BaseModel):
    """Schema for creating a new chat message."""
    role: MessageRoleEnum
    content: str
    sequence_number: int
    token_count: Optional[int] = None
    ai_model: Optional[str] = None
    completion_tokens: Optional[int] = None
    prompt_tokens: Optional[int] = None
    references: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatMessageResponse(BaseModel):
    """Schema for chat message response."""
    id: UUID
    session_id: UUID
    role: str
    content: str
    sequence_number: int
    token_count: Optional[int] = None
    ai_model: Optional[str] = None
    completion_tokens: Optional[int] = None
    prompt_tokens: Optional[int] = None
    references: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Chat Session Schemas ============

class ChatSessionCreate(BaseModel):
    """Schema for creating a new chat session."""
    title: Optional[str] = None
    source: ChatSourceEnum = ChatSourceEnum.COPILOT
    external_id: Optional[str] = None
    ai_model: Optional[str] = None
    agent_name: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    started_at: Optional[datetime] = None


class ChatSessionUpdate(BaseModel):
    """Schema for updating a chat session."""
    title: Optional[str] = None
    ai_model: Optional[str] = None
    agent_name: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_archived: Optional[bool] = None
    ended_at: Optional[datetime] = None


class ChatSessionResponse(BaseModel):
    """Schema for chat session response."""
    id: UUID
    title: Optional[str] = None
    source: str
    external_id: Optional[str] = None
    ai_model: Optional[str] = None
    agent_name: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_backed_up: bool
    backup_location: Optional[str] = None
    last_backup_at: Optional[datetime] = None
    is_active: bool
    is_archived: bool
    started_at: datetime
    ended_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    message_count: int = 0

    class Config:
        from_attributes = True


class ChatSessionWithMessages(ChatSessionResponse):
    """Schema for chat session response with messages."""
    messages: List[ChatMessageResponse] = Field(default_factory=list)


# ============ Import/Export Schemas ============

class ChatImportMessage(BaseModel):
    """Schema for importing a single message."""
    role: MessageRoleEnum
    content: str
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatImportRequest(BaseModel):
    """Schema for importing chat history from external source."""
    title: Optional[str] = None
    source: ChatSourceEnum = ChatSourceEnum.EXTERNAL_IMPORT
    external_id: Optional[str] = None
    ai_model: Optional[str] = None
    messages: List[ChatImportMessage]
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatExportResponse(BaseModel):
    """Schema for exported chat data."""
    session: ChatSessionResponse
    messages: List[ChatMessageResponse]
    exported_at: datetime
    export_format: str = "json"


class BulkImportRequest(BaseModel):
    """Schema for bulk importing multiple chat sessions."""
    sessions: List[ChatImportRequest]


class BulkImportResponse(BaseModel):
    """Schema for bulk import response."""
    imported_count: int
    failed_count: int
    session_ids: List[UUID]
    errors: List[Dict[str, Any]] = Field(default_factory=list)


# ============ Backup Schemas ============

class BackupRequest(BaseModel):
    """Schema for backup request."""
    session_ids: Optional[List[UUID]] = None  # If None, backup all unbackedup sessions
    backup_location: Optional[str] = None  # Override default backup location
    include_archived: bool = False


class BackupResponse(BaseModel):
    """Schema for backup response."""
    backup_id: str
    sessions_backed_up: int
    backup_location: str
    backup_size_bytes: int
    backed_up_at: datetime


class BackupStatus(BaseModel):
    """Schema for backup status."""
    last_backup_at: Optional[datetime] = None
    total_sessions: int
    backed_up_sessions: int
    pending_sessions: int
    next_scheduled_backup: Optional[datetime] = None


# ============ Decision Context Schemas ============

class DecisionContextCreate(BaseModel):
    """Schema for creating a decision context."""
    title: str
    category: Optional[str] = None
    summary: str
    key_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    action_items: List[Dict[str, Any]] = Field(default_factory=list)
    context_data: Dict[str, Any] = Field(default_factory=dict)
    source_session_ids: List[UUID] = Field(default_factory=list)
    priority: PriorityEnum = PriorityEnum.NORMAL
    valid_until: Optional[datetime] = None


class DecisionContextUpdate(BaseModel):
    """Schema for updating a decision context."""
    title: Optional[str] = None
    category: Optional[str] = None
    summary: Optional[str] = None
    key_decisions: Optional[List[Dict[str, Any]]] = None
    action_items: Optional[List[Dict[str, Any]]] = None
    context_data: Optional[Dict[str, Any]] = None
    priority: Optional[PriorityEnum] = None
    status: Optional[str] = None
    valid_until: Optional[datetime] = None


class DecisionContextResponse(BaseModel):
    """Schema for decision context response."""
    id: UUID
    title: str
    category: Optional[str] = None
    summary: str
    key_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    action_items: List[Dict[str, Any]] = Field(default_factory=list)
    context_data: Dict[str, Any] = Field(default_factory=dict)
    source_session_ids: List[UUID] = Field(default_factory=list)
    source_count: int
    priority: str
    status: str
    valid_from: datetime
    valid_until: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UnifyContextRequest(BaseModel):
    """Schema for requesting context unification."""
    session_ids: List[UUID]
    title: str
    category: Optional[str] = None
    priority: PriorityEnum = PriorityEnum.NORMAL
    include_action_items: bool = True


class UnifiedContextResponse(BaseModel):
    """Schema for unified context response."""
    context: DecisionContextResponse
    source_sessions: List[ChatSessionResponse]
    synthesis_notes: Optional[str] = None


# ============ Disruption Event Schemas ============

class DisruptionEventCreate(BaseModel):
    """Schema for creating a disruption event."""
    event_type: str
    description: Optional[str] = None
    session_id: Optional[UUID] = None
    previous_state: Dict[str, Any] = Field(default_factory=dict)
    new_state: Dict[str, Any] = Field(default_factory=dict)
    impact_level: ImpactLevelEnum = ImpactLevelEnum.LOW


class DisruptionEventUpdate(BaseModel):
    """Schema for updating a disruption event."""
    resolved: Optional[bool] = None
    resolution_notes: Optional[str] = None


class DisruptionEventResponse(BaseModel):
    """Schema for disruption event response."""
    id: UUID
    event_type: str
    description: Optional[str] = None
    session_id: Optional[UUID] = None
    previous_state: Dict[str, Any] = Field(default_factory=dict)
    new_state: Dict[str, Any] = Field(default_factory=dict)
    impact_level: str
    resolved: bool
    resolution_notes: Optional[str] = None
    occurred_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ Dashboard/Summary Schemas ============

class ChatBackupDashboard(BaseModel):
    """Dashboard overview of chat backup system."""
    total_sessions: int
    active_sessions: int
    archived_sessions: int
    total_messages: int
    backup_status: BackupStatus
    recent_disruptions: List[DisruptionEventResponse]
    active_contexts: int
    last_unification_at: Optional[datetime] = None
