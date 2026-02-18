"""Add SupportForge tables

Revision ID: supportforge_001
Revises: 
Create Date: 2026-02-18 17:17:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'supportforge_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create supportforge_tenants table
    op.create_table(
        'supportforge_tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('subdomain', sa.String(), nullable=False),
        sa.Column('plan', sa.String(), nullable=False, server_default='starter'),
        sa.Column('settings', postgresql.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('subdomain')
    )
    
    # Create supportforge_agents table
    op.create_table(
        'supportforge_agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False, server_default='agent'),
        sa.Column('departments', postgresql.ARRAY(sa.String()), server_default='{}'),
        sa.Column('skills', postgresql.ARRAY(sa.String()), server_default='{}'),
        sa.Column('status', sa.String(), nullable=False, server_default='offline'),
        sa.Column('max_concurrent_tickets', sa.Integer(), server_default='10'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['supportforge_tenants.id'])
    )
    
    # Create supportforge_customers table
    op.create_table(
        'supportforge_customers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('phone', sa.String()),
        sa.Column('company', sa.String()),
        sa.Column('empire_product_id', postgresql.UUID(as_uuid=True)),
        sa.Column('empire_product_type', sa.String()),
        sa.Column('metadata', postgresql.JSON(), server_default='{}'),
        sa.Column('tags', postgresql.ARRAY(sa.String()), server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['supportforge_tenants.id'])
    )
    
    # Create supportforge_sla_policies table
    op.create_table(
        'supportforge_sla_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('first_response_time_minutes', sa.Integer(), nullable=False),
        sa.Column('resolution_time_minutes', sa.Integer(), nullable=False),
        sa.Column('business_hours_only', sa.Boolean(), server_default='false'),
        sa.Column('priority_multipliers', postgresql.JSON(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['supportforge_tenants.id'])
    )
    
    # Create supportforge_tickets table
    op.create_table(
        'supportforge_tickets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ticket_number', sa.Integer(), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_agent_id', postgresql.UUID(as_uuid=True)),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='new'),
        sa.Column('priority', sa.String(), nullable=False, server_default='normal'),
        sa.Column('channel', sa.String(), nullable=False),
        sa.Column('tags', postgresql.ARRAY(sa.String()), server_default='{}'),
        sa.Column('category', sa.String()),
        sa.Column('sla_policy_id', postgresql.UUID(as_uuid=True)),
        sa.Column('first_response_at', sa.DateTime(timezone=True)),
        sa.Column('resolved_at', sa.DateTime(timezone=True)),
        sa.Column('closed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['supportforge_tenants.id']),
        sa.ForeignKeyConstraint(['customer_id'], ['supportforge_customers.id']),
        sa.ForeignKeyConstraint(['assigned_agent_id'], ['supportforge_agents.id']),
        sa.ForeignKeyConstraint(['sla_policy_id'], ['supportforge_sla_policies.id'])
    )
    
    # Create supportforge_messages table
    op.create_table(
        'supportforge_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ticket_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_type', sa.String(), nullable=False),
        sa.Column('sender_id', postgresql.UUID(as_uuid=True)),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_html', sa.Text()),
        sa.Column('is_internal_note', sa.Boolean(), server_default='false'),
        sa.Column('attachments', postgresql.JSON(), server_default='[]'),
        sa.Column('ai_suggested', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['ticket_id'], ['supportforge_tickets.id'])
    )
    
    # Create supportforge_kb_articles table
    op.create_table(
        'supportforge_kb_articles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_html', sa.Text()),
        sa.Column('category_id', postgresql.UUID(as_uuid=True)),
        sa.Column('tags', postgresql.ARRAY(sa.String()), server_default='{}'),
        sa.Column('status', sa.String(), nullable=False, server_default='draft'),
        sa.Column('view_count', sa.Integer(), server_default='0'),
        sa.Column('helpful_count', sa.Integer(), server_default='0'),
        sa.Column('not_helpful_count', sa.Integer(), server_default='0'),
        sa.Column('author_id', postgresql.UUID(as_uuid=True)),
        sa.Column('published_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['supportforge_tenants.id']),
        sa.ForeignKeyConstraint(['author_id'], ['supportforge_agents.id'])
    )
    
    # Create supportforge_automations table
    op.create_table(
        'supportforge_automations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('trigger_type', sa.String(), nullable=False),
        sa.Column('conditions', postgresql.JSON(), nullable=False, server_default='{}'),
        sa.Column('actions', postgresql.JSON(), nullable=False, server_default='[]'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('execution_count', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['supportforge_tenants.id'])
    )
    
    # Create supportforge_integrations table
    op.create_table(
        'supportforge_integrations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('integration_type', sa.String(), nullable=False),
        sa.Column('config', postgresql.JSON(), nullable=False, server_default='{}'),
        sa.Column('api_key', sa.String()),
        sa.Column('webhook_url', sa.String()),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['supportforge_tenants.id'])
    )
    
    # Create indexes for performance
    op.create_index('idx_supportforge_tickets_tenant_status', 'supportforge_tickets', ['tenant_id', 'status'])
    op.create_index('idx_supportforge_tickets_customer', 'supportforge_tickets', ['customer_id'])
    op.create_index('idx_supportforge_tickets_agent', 'supportforge_tickets', ['assigned_agent_id'])
    op.create_index('idx_supportforge_messages_ticket', 'supportforge_messages', ['ticket_id'])
    op.create_index('idx_supportforge_customers_tenant_email', 'supportforge_customers', ['tenant_id', 'email'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_supportforge_customers_tenant_email')
    op.drop_index('idx_supportforge_messages_ticket')
    op.drop_index('idx_supportforge_tickets_agent')
    op.drop_index('idx_supportforge_tickets_customer')
    op.drop_index('idx_supportforge_tickets_tenant_status')
    
    # Drop tables in reverse order
    op.drop_table('supportforge_integrations')
    op.drop_table('supportforge_automations')
    op.drop_table('supportforge_kb_articles')
    op.drop_table('supportforge_messages')
    op.drop_table('supportforge_tickets')
    op.drop_table('supportforge_sla_policies')
    op.drop_table('supportforge_customers')
    op.drop_table('supportforge_agents')
    op.drop_table('supportforge_tenants')
