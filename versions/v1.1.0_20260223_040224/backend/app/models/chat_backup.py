"""
Chat Backup and Decision Context database models.
Stores chat sessions, messages, and unified decision context for consistent decision-making.
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, func, Text, Integer, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
import enum
from app.database import Base


class ChatSource(str, enum.Enum):
    """Source/origin of chat messages."""
    COPILOT = "copilot"
    AI_AGENT = "ai_agent"
    USER = "user"
    EXTERNAL_IMPORT = "external_import"
    SYSTEM = "system"


class ChatMessageRole(str, enum.Enum):
    """Role of the message sender."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatSession(Base):
    """
    Represents a chat session containing multiple messages.
    Sessions are periodically backed up and can be imported from external sources.
    """
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Session identification
    title = Column(String(500), nullable=True)
    source = Column(String(50), nullable=False, default=ChatSource.COPILOT.value)
    external_id = Column(String(255), nullable=True)  # ID from source platform
    
    # Session metadata
    ai_model = Column(String(100), nullable=True)  # e.g., "gpt-4", "claude-3"
    agent_name = Column(String(100), nullable=True)  # Name of AI agent if applicable
    
    # Tags and context
    tags = Column(JSONB, nullable=False, default=list)
    session_metadata = Column(JSONB, nullable=False, default=dict)
    
    # Backup tracking
    is_backed_up = Column(Boolean, default=False)
    backup_location = Column(String(500), nullable=True)  # Local path or cloud URL
    last_backup_at = Column(DateTime(timezone=True), nullable=True)
    
    # Session status
    is_active = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ChatSession {self.id} - {self.source}>"


class ChatMessage(Base):
    """
    Individual message within a chat session.
    Stores both user and AI messages with full context.
    """
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False, index=True)
    
    # Message content
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    
    # Message metadata
    sequence_number = Column(Integer, nullable=False)  # Order within session
    token_count = Column(Integer, nullable=True)  # Estimated token count
    
    # AI-specific metadata
    ai_model = Column(String(100), nullable=True)  # Model used for this specific response
    completion_tokens = Column(Integer, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    
    # Context and references
    references = Column(JSONB, nullable=False, default=list)  # File refs, URLs, etc.
    message_metadata = Column(JSONB, nullable=False, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self):
        return f"<ChatMessage {self.id} - {self.role}>"


class DecisionContext(Base):
    """
    Unified decision context synthesized from multiple chat sessions.
    Provides consistent context for AI agents and decision-making.
    """
    __tablename__ = "decision_contexts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Context identification
    title = Column(String(500), nullable=False)
    category = Column(String(100), nullable=True)  # e.g., "product", "strategy", "technical"
    
    # Unified context content
    summary = Column(Text, nullable=False)  # Synthesized summary from chat sessions
    key_decisions = Column(JSONB, nullable=False, default=list)  # List of key decisions made
    action_items = Column(JSONB, nullable=False, default=list)  # Pending action items
    context_data = Column(JSONB, nullable=False, default=dict)  # Additional structured context
    
    # Source tracking
    source_session_ids = Column(JSONB, nullable=False, default=list)  # IDs of contributing sessions
    source_count = Column(Integer, nullable=False, default=0)
    
    # Priority and status
    priority = Column(String(20), nullable=False, default="normal")  # low, normal, high, critical
    status = Column(String(20), nullable=False, default="active")  # active, archived, superseded
    
    # Validity
    valid_from = Column(DateTime(timezone=True), server_default=func.now())
    valid_until = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<DecisionContext {self.id} - {self.title}>"


class DisruptionEvent(Base):
    """
    Log of disruption events (model switches, assignment changes, etc.)
    Used for tracking and analyzing workflow disruptions.
    """
    __tablename__ = "disruption_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Event details
    event_type = Column(String(50), nullable=False)  # model_switch, assignment_change, context_loss
    description = Column(Text, nullable=True)
    
    # Related entities
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=True, index=True)
    
    # Context before/after
    previous_state = Column(JSONB, nullable=False, default=dict)
    new_state = Column(JSONB, nullable=False, default=dict)
    
    # Impact assessment
    impact_level = Column(String(20), nullable=False, default="low")  # low, medium, high
    resolved = Column(Boolean, default=False)
    resolution_notes = Column(Text, nullable=True)
    
    # Timestamps
    occurred_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<DisruptionEvent {self.id} - {self.event_type}>"
