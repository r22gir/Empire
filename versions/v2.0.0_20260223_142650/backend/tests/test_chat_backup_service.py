"""
Unit tests for Chat Backup and Decision Context System.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from app.services.chat_backup_service import ChatBackupService
from app.services.context_unification_service import ContextUnificationService
from app.schemas.chat_backup import (
    ChatSessionCreate, ChatSessionUpdate, ChatMessageCreate,
    ChatImportRequest, ChatImportMessage, BackupRequest,
    DecisionContextCreate, DisruptionEventCreate,
    ChatSourceEnum, MessageRoleEnum, PriorityEnum, ImpactLevelEnum
)


class TestChatBackupService:
    """Test suite for ChatBackupService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.flush = AsyncMock()
        return db

    @pytest.fixture
    def chat_backup_service(self, mock_db):
        """Create ChatBackupService instance with mock DB."""
        return ChatBackupService(mock_db)

    def test_service_initialization(self, chat_backup_service):
        """Test service initializes correctly."""
        assert chat_backup_service is not None
        assert chat_backup_service.default_backup_dir is not None

    @pytest.mark.asyncio
    async def test_create_session(self, mock_db, chat_backup_service):
        """Test creating a chat session."""
        session_data = ChatSessionCreate(
            title="Test Session",
            source=ChatSourceEnum.COPILOT,
            ai_model="gpt-4",
            tags=["test", "unit-test"]
        )

        # Mock the session object that would be returned
        mock_session = MagicMock()
        mock_session.id = uuid.uuid4()
        mock_session.title = session_data.title
        mock_session.source = session_data.source.value
        mock_session.ai_model = session_data.ai_model
        mock_session.tags = session_data.tags

        # Refresh should populate the mock session
        async def mock_refresh(obj):
            for attr in ['id', 'title', 'source', 'ai_model', 'tags']:
                setattr(obj, attr, getattr(mock_session, attr))
        mock_db.refresh = mock_refresh

        result = await chat_backup_service.create_session(session_data)

        mock_db.add.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_sessions_empty(self, mock_db, chat_backup_service):
        """Test getting sessions when none exist."""
        # Create proper async mock for query result
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        
        mock_db.execute = AsyncMock(return_value=mock_result)

        sessions = await chat_backup_service.get_sessions()

        assert sessions == []

    @pytest.mark.asyncio
    async def test_import_chat(self, mock_db, chat_backup_service):
        """Test importing a chat session."""
        import_data = ChatImportRequest(
            title="Imported Chat",
            source=ChatSourceEnum.EXTERNAL_IMPORT,
            messages=[
                ChatImportMessage(role=MessageRoleEnum.USER, content="Hello"),
                ChatImportMessage(role=MessageRoleEnum.ASSISTANT, content="Hi there!")
            ],
            tags=["imported"]
        )

        # Setup mock session
        mock_session = MagicMock()
        mock_session.id = uuid.uuid4()
        mock_session.title = import_data.title

        async def mock_refresh(obj):
            obj.id = mock_session.id
            obj.title = mock_session.title
        mock_db.refresh = mock_refresh

        result = await chat_backup_service.import_chat(import_data)

        # Verify session and messages were added
        assert mock_db.add.call_count >= 1  # Session + messages
        assert result is not None

    def test_session_create_schema_validation(self):
        """Test session create schema validation."""
        # Valid session
        session = ChatSessionCreate(
            title="Test",
            source=ChatSourceEnum.COPILOT
        )
        assert session.title == "Test"
        assert session.source == ChatSourceEnum.COPILOT

        # Default values
        session_defaults = ChatSessionCreate()
        assert session_defaults.source == ChatSourceEnum.COPILOT
        assert session_defaults.tags == []
        assert session_defaults.metadata == {}

    def test_message_create_schema_validation(self):
        """Test message create schema validation."""
        message = ChatMessageCreate(
            role=MessageRoleEnum.USER,
            content="Test message",
            sequence_number=1
        )
        assert message.role == MessageRoleEnum.USER
        assert message.content == "Test message"
        assert message.sequence_number == 1

    def test_import_message_schema_validation(self):
        """Test import message schema validation."""
        message = ChatImportMessage(
            role=MessageRoleEnum.ASSISTANT,
            content="AI response",
            timestamp=datetime.now(timezone.utc)
        )
        assert message.role == MessageRoleEnum.ASSISTANT
        assert message.content == "AI response"
        assert message.timestamp is not None


class TestContextUnificationService:
    """Test suite for ContextUnificationService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def unification_service(self, mock_db):
        """Create ContextUnificationService instance with mock DB."""
        return ContextUnificationService(mock_db)

    def test_service_initialization(self, unification_service):
        """Test service initializes correctly."""
        assert unification_service is not None

    @pytest.mark.asyncio
    async def test_create_context(self, mock_db, unification_service):
        """Test creating a decision context."""
        context_data = DecisionContextCreate(
            title="Test Decision Context",
            category="technical",
            summary="This is a test summary of decisions made.",
            key_decisions=[{"decision": "Use Python", "rationale": "Team expertise"}],
            action_items=[{"action": "Setup project", "status": "pending"}],
            priority=PriorityEnum.HIGH
        )

        # Mock context
        mock_context = MagicMock()
        mock_context.id = uuid.uuid4()
        mock_context.title = context_data.title

        async def mock_refresh(obj):
            obj.id = mock_context.id
            obj.title = mock_context.title
        mock_db.refresh = mock_refresh

        result = await unification_service.create_context(context_data)

        mock_db.add.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_active_contexts_empty(self, mock_db, unification_service):
        """Test getting active contexts when none exist."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        
        mock_db.execute = AsyncMock(return_value=mock_result)

        contexts = await unification_service.get_active_contexts()

        assert contexts == []

    @pytest.mark.asyncio
    async def test_get_unified_context_for_agents_no_context(self, mock_db, unification_service):
        """Test getting unified context when none exists."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await unification_service.get_unified_context_for_agents()

        assert result["status"] == "no_context"
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_log_disruption(self, mock_db, unification_service):
        """Test logging a disruption event."""
        event_data = DisruptionEventCreate(
            event_type="model_switch",
            description="Switched from GPT-4 to Claude",
            previous_state={"model": "gpt-4"},
            new_state={"model": "claude-3"},
            impact_level=ImpactLevelEnum.MEDIUM
        )

        # Mock event
        mock_event = MagicMock()
        mock_event.id = uuid.uuid4()
        mock_event.event_type = event_data.event_type

        async def mock_refresh(obj):
            obj.id = mock_event.id
            obj.event_type = mock_event.event_type
        mock_db.refresh = mock_refresh

        result = await unification_service.log_disruption(event_data)

        mock_db.add.assert_called_once()
        assert result is not None

    def test_context_create_schema_validation(self):
        """Test context create schema validation."""
        context = DecisionContextCreate(
            title="Test Context",
            summary="Test summary",
            priority=PriorityEnum.NORMAL
        )
        assert context.title == "Test Context"
        assert context.summary == "Test summary"
        assert context.priority == PriorityEnum.NORMAL
        assert context.key_decisions == []
        assert context.action_items == []

    def test_disruption_event_schema_validation(self):
        """Test disruption event schema validation."""
        event = DisruptionEventCreate(
            event_type="context_loss",
            description="Lost context due to session timeout",
            impact_level=ImpactLevelEnum.HIGH
        )
        assert event.event_type == "context_loss"
        assert event.impact_level == ImpactLevelEnum.HIGH
        assert event.previous_state == {}
        assert event.new_state == {}


class TestChatBackupSchemas:
    """Test suite for Chat Backup schemas."""

    def test_chat_source_enum(self):
        """Test ChatSourceEnum values."""
        assert ChatSourceEnum.COPILOT.value == "copilot"
        assert ChatSourceEnum.AI_AGENT.value == "ai_agent"
        assert ChatSourceEnum.USER.value == "user"
        assert ChatSourceEnum.EXTERNAL_IMPORT.value == "external_import"
        assert ChatSourceEnum.SYSTEM.value == "system"

    def test_message_role_enum(self):
        """Test MessageRoleEnum values."""
        assert MessageRoleEnum.USER.value == "user"
        assert MessageRoleEnum.ASSISTANT.value == "assistant"
        assert MessageRoleEnum.SYSTEM.value == "system"

    def test_priority_enum(self):
        """Test PriorityEnum values."""
        assert PriorityEnum.LOW.value == "low"
        assert PriorityEnum.NORMAL.value == "normal"
        assert PriorityEnum.HIGH.value == "high"
        assert PriorityEnum.CRITICAL.value == "critical"

    def test_impact_level_enum(self):
        """Test ImpactLevelEnum values."""
        assert ImpactLevelEnum.LOW.value == "low"
        assert ImpactLevelEnum.MEDIUM.value == "medium"
        assert ImpactLevelEnum.HIGH.value == "high"

    def test_backup_request_defaults(self):
        """Test BackupRequest default values."""
        request = BackupRequest()
        assert request.session_ids is None
        assert request.backup_location is None
        assert request.include_archived is False

    def test_backup_request_with_session_ids(self):
        """Test BackupRequest with session IDs."""
        session_ids = [uuid.uuid4(), uuid.uuid4()]
        request = BackupRequest(
            session_ids=session_ids,
            backup_location="/custom/backup/path",
            include_archived=True
        )
        assert request.session_ids == session_ids
        assert request.backup_location == "/custom/backup/path"
        assert request.include_archived is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
