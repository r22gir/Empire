"""Add SupportForge tables

Revision ID: supportforge_001
Revises: 
Create Date: 2026-02-18 17:19:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'supportforge_001'
down_revision = None  # Update this if there are previous migrations
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create SupportForge tables."""
    
    # Tenants table
    op.create_table('sf_tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('subdomain', sa.String(100), unique=True, nullable=False),
        sa.Column('plan', sa.String(50), nullable=False, server_default='starter'),
        sa.Column('settings', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True))
    )
    
    # Support Agents table
    op.create_table('sf_support_agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='agent'),
        sa.Column('departments', postgresql.ARRAY(sa.String), server_default='{}'),
        sa.Column('skills', postgresql.ARRAY(sa.String), server_default='{}'),
        sa.Column('status', sa.String(20), server_default='offline'),
        sa.Column('max_concurrent_tickets', sa.Integer, server_default='10'),
        sa.Column('avatar_url', sa.String),
        sa.Column('last_active_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['sf_tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'email')
    )
    
    # Customers table
    op.create_table('sf_customers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255)),
        sa.Column('phone', sa.String(50)),
        sa.Column('company', sa.String(255)),
        sa.Column('empire_product_type', sa.String(100)),
        sa.Column('empire_product_id', postgresql.UUID(as_uuid=True)),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('tags', postgresql.ARRAY(sa.String), server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True)),
        sa.ForeignKeyConstraint(['tenant_id'], ['sf_tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'email')
    )
    op.create_index('idx_sf_customers_email', 'sf_customers', ['email'])
    op.create_index('idx_sf_customers_empire', 'sf_customers', ['empire_product_type', 'empire_product_id'])
    
    # Tickets table
    op.create_table('sf_tickets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ticket_number', sa.Integer, nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_agent_id', postgresql.UUID(as_uuid=True)),
        sa.Column('subject', sa.String, nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='new'),
        sa.Column('priority', sa.String(20), nullable=False, server_default='normal'),
        sa.Column('channel', sa.String(50), nullable=False),
        sa.Column('tags', postgresql.ARRAY(sa.String), server_default='{}'),
        sa.Column('category', sa.String(100)),
        sa.Column('sla_policy_id', postgresql.UUID(as_uuid=True)),
        sa.Column('first_response_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('resolved_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('closed_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True)),
        sa.ForeignKeyConstraint(['tenant_id'], ['sf_tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['customer_id'], ['sf_customers.id']),
        sa.ForeignKeyConstraint(['assigned_agent_id'], ['sf_support_agents.id'])
    )
    op.create_index('idx_sf_tickets_tenant', 'sf_tickets', ['tenant_id'])
    op.create_index('idx_sf_tickets_status', 'sf_tickets', ['status'])
    op.create_index('idx_sf_tickets_assigned', 'sf_tickets', ['assigned_agent_id'])
    op.create_index('idx_sf_tickets_created', 'sf_tickets', ['created_at'])
    
    # Messages table
    op.create_table('sf_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ticket_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_type', sa.String(20), nullable=False),
        sa.Column('sender_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.String, nullable=False),
        sa.Column('content_html', sa.String),
        sa.Column('is_internal_note', sa.Boolean, server_default='false'),
        sa.Column('attachments', postgresql.JSONB, server_default='[]'),
        sa.Column('ai_suggested', sa.Boolean, server_default='false'),
        sa.Column('ai_confidence', sa.Numeric(5, 2)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['ticket_id'], ['sf_tickets.id'], ondelete='CASCADE')
    )
    op.create_index('idx_sf_messages_ticket', 'sf_messages', ['ticket_id'])
    
    # KB Categories table
    op.create_table('sf_kb_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False),
        sa.Column('description', sa.String),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True)),
        sa.Column('sort_order', sa.Integer, server_default='0'),
        sa.ForeignKeyConstraint(['tenant_id'], ['sf_tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['sf_kb_categories.id']),
        sa.UniqueConstraint('tenant_id', 'slug')
    )
    
    # KB Articles table
    op.create_table('sf_kb_articles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('slug', sa.String(500), nullable=False),
        sa.Column('content', sa.String, nullable=False),
        sa.Column('content_html', sa.String, nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True)),
        sa.Column('tags', postgresql.ARRAY(sa.String), server_default='{}'),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('view_count', sa.Integer, server_default='0'),
        sa.Column('helpful_count', sa.Integer, server_default='0'),
        sa.Column('not_helpful_count', sa.Integer, server_default='0'),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('published_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True)),
        sa.ForeignKeyConstraint(['tenant_id'], ['sf_tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['sf_kb_categories.id']),
        sa.ForeignKeyConstraint(['author_id'], ['sf_support_agents.id']),
        sa.UniqueConstraint('tenant_id', 'slug')
    )
    
    # Automations table
    op.create_table('sf_automations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('trigger_type', sa.String(50), nullable=False),
        sa.Column('conditions', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('actions', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('execution_count', sa.Integer, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['sf_tenants.id'], ondelete='CASCADE')
    )
    
    # SLA Policies table
    op.create_table('sf_sla_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('first_response_minutes', sa.Integer, nullable=False),
        sa.Column('resolution_minutes', sa.Integer, nullable=False),
        sa.Column('business_hours_only', sa.Boolean, server_default='true'),
        sa.Column('priority_multipliers', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['sf_tenants.id'], ondelete='CASCADE')
    )
    
    # Canned Responses table
    op.create_table('sf_canned_responses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('shortcut', sa.String(50)),
        sa.Column('content', sa.String, nullable=False),
        sa.Column('category', sa.String(100)),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['sf_tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['sf_support_agents.id'])
    )
    
    # Integrations table
    op.create_table('sf_integrations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('integration_type', sa.String(100), nullable=False),
        sa.Column('config', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('api_key', sa.String(500)),
        sa.Column('webhook_url', sa.String),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('last_sync_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['sf_tenants.id'], ondelete='CASCADE')
    )
    
    # Satisfaction Ratings table
    op.create_table('sf_satisfaction_ratings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ticket_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rating', sa.Integer, nullable=False),
        sa.Column('comment', sa.String),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['ticket_id'], ['sf_tickets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['customer_id'], ['sf_customers.id']),
        sa.CheckConstraint('rating >= 1 AND rating <= 5', name='check_rating_range')
    )


def downgrade() -> None:
    """Drop SupportForge tables."""
    op.drop_table('sf_satisfaction_ratings')
    op.drop_table('sf_integrations')
    op.drop_table('sf_canned_responses')
    op.drop_table('sf_sla_policies')
    op.drop_table('sf_automations')
    op.drop_table('sf_kb_articles')
    op.drop_table('sf_kb_categories')
    op.drop_table('sf_messages')
    op.drop_table('sf_tickets')
    op.drop_table('sf_customers')
    op.drop_table('sf_support_agents')
    op.drop_table('sf_tenants')
