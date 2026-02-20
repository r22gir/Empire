"""add chat backup and decision context tables

Revision ID: 002_chat_backup
Revises: 001_economic
Create Date: 2026-02-20 15:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_chat_backup'
down_revision = '001_economic'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create chat_sessions table
    op.create_table(
        'chat_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='copilot'),
        sa.Column('external_id', sa.String(length=255), nullable=True),
        sa.Column('ai_model', sa.String(length=100), nullable=True),
        sa.Column('agent_name', sa.String(length=100), nullable=True),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('session_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('is_backed_up', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('backup_location', sa.String(length=500), nullable=True),
        sa.Column('last_backup_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for chat_sessions
    op.create_index('ix_chat_sessions_source', 'chat_sessions', ['source'])
    op.create_index('ix_chat_sessions_is_backed_up', 'chat_sessions', ['is_backed_up'])
    op.create_index('ix_chat_sessions_is_active', 'chat_sessions', ['is_active'])
    op.create_index('ix_chat_sessions_is_archived', 'chat_sessions', ['is_archived'])
    op.create_index('ix_chat_sessions_started_at', 'chat_sessions', ['started_at'])
    op.create_index('ix_chat_sessions_created_at', 'chat_sessions', ['created_at'])
    
    # Create GIN index for JSONB tags column
    op.create_index(
        'ix_chat_sessions_tags_gin',
        'chat_sessions',
        ['tags'],
        postgresql_using='gin'
    )
    
    # Create chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('sequence_number', sa.Integer(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('ai_model', sa.String(length=100), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), nullable=True),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('references', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('message_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for chat_messages
    op.create_index('ix_chat_messages_session_id', 'chat_messages', ['session_id'])
    op.create_index('ix_chat_messages_role', 'chat_messages', ['role'])
    op.create_index('ix_chat_messages_created_at', 'chat_messages', ['created_at'])
    op.create_index('ix_chat_messages_session_sequence', 'chat_messages', ['session_id', 'sequence_number'])
    
    # Create decision_contexts table
    op.create_table(
        'decision_contexts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('key_decisions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('action_items', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('context_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('source_session_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('source_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('priority', sa.String(length=20), nullable=False, server_default='normal'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('valid_from', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for decision_contexts
    op.create_index('ix_decision_contexts_category', 'decision_contexts', ['category'])
    op.create_index('ix_decision_contexts_priority', 'decision_contexts', ['priority'])
    op.create_index('ix_decision_contexts_status', 'decision_contexts', ['status'])
    op.create_index('ix_decision_contexts_created_at', 'decision_contexts', ['created_at'])
    op.create_index('ix_decision_contexts_valid_from', 'decision_contexts', ['valid_from'])
    
    # Create GIN index for JSONB columns
    op.create_index(
        'ix_decision_contexts_key_decisions_gin',
        'decision_contexts',
        ['key_decisions'],
        postgresql_using='gin'
    )
    op.create_index(
        'ix_decision_contexts_action_items_gin',
        'decision_contexts',
        ['action_items'],
        postgresql_using='gin'
    )
    
    # Create disruption_events table
    op.create_table(
        'disruption_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('previous_state', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('new_state', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('impact_level', sa.String(length=20), nullable=False, server_default='low'),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for disruption_events
    op.create_index('ix_disruption_events_event_type', 'disruption_events', ['event_type'])
    op.create_index('ix_disruption_events_session_id', 'disruption_events', ['session_id'])
    op.create_index('ix_disruption_events_impact_level', 'disruption_events', ['impact_level'])
    op.create_index('ix_disruption_events_resolved', 'disruption_events', ['resolved'])
    op.create_index('ix_disruption_events_occurred_at', 'disruption_events', ['occurred_at'])


def downgrade() -> None:
    # Drop indexes for disruption_events
    op.drop_index('ix_disruption_events_occurred_at', table_name='disruption_events')
    op.drop_index('ix_disruption_events_resolved', table_name='disruption_events')
    op.drop_index('ix_disruption_events_impact_level', table_name='disruption_events')
    op.drop_index('ix_disruption_events_session_id', table_name='disruption_events')
    op.drop_index('ix_disruption_events_event_type', table_name='disruption_events')
    
    # Drop disruption_events table
    op.drop_table('disruption_events')
    
    # Drop indexes for decision_contexts
    op.drop_index('ix_decision_contexts_action_items_gin', table_name='decision_contexts')
    op.drop_index('ix_decision_contexts_key_decisions_gin', table_name='decision_contexts')
    op.drop_index('ix_decision_contexts_valid_from', table_name='decision_contexts')
    op.drop_index('ix_decision_contexts_created_at', table_name='decision_contexts')
    op.drop_index('ix_decision_contexts_status', table_name='decision_contexts')
    op.drop_index('ix_decision_contexts_priority', table_name='decision_contexts')
    op.drop_index('ix_decision_contexts_category', table_name='decision_contexts')
    
    # Drop decision_contexts table
    op.drop_table('decision_contexts')
    
    # Drop indexes for chat_messages
    op.drop_index('ix_chat_messages_session_sequence', table_name='chat_messages')
    op.drop_index('ix_chat_messages_created_at', table_name='chat_messages')
    op.drop_index('ix_chat_messages_role', table_name='chat_messages')
    op.drop_index('ix_chat_messages_session_id', table_name='chat_messages')
    
    # Drop chat_messages table
    op.drop_table('chat_messages')
    
    # Drop indexes for chat_sessions
    op.drop_index('ix_chat_sessions_tags_gin', table_name='chat_sessions')
    op.drop_index('ix_chat_sessions_created_at', table_name='chat_sessions')
    op.drop_index('ix_chat_sessions_started_at', table_name='chat_sessions')
    op.drop_index('ix_chat_sessions_is_archived', table_name='chat_sessions')
    op.drop_index('ix_chat_sessions_is_active', table_name='chat_sessions')
    op.drop_index('ix_chat_sessions_is_backed_up', table_name='chat_sessions')
    op.drop_index('ix_chat_sessions_source', table_name='chat_sessions')
    
    # Drop chat_sessions table
    op.drop_table('chat_sessions')
