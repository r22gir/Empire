"""add economic intelligence tables

Revision ID: 001_economic
Revises: 
Create Date: 2026-02-18 17:11:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_economic'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create economic_ledgers table
    op.create_table(
        'economic_ledgers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('balance', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'),
        sa.Column('total_income', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'),
        sa.Column('total_costs', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'),
        sa.Column('total_profit', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'),
        sa.Column('transaction_count', sa.Numeric(precision=10, scale=0), nullable=False, server_default='0'),
        sa.Column('last_transaction_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='stable'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for economic_ledgers
    op.create_index('ix_economic_ledgers_entity_type', 'economic_ledgers', ['entity_type'])
    op.create_index('ix_economic_ledgers_entity_id', 'economic_ledgers', ['entity_id'])
    op.create_index('ix_economic_ledgers_entity', 'economic_ledgers', ['entity_type', 'entity_id'])
    op.create_index('ix_economic_ledgers_created_at', 'economic_ledgers', ['created_at'])
    
    # Create economic_transactions table
    op.create_table(
        'economic_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ledger_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_type', sa.String(length=50), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('resource_details', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('quality_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['ledger_id'], ['economic_ledgers.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for economic_transactions
    op.create_index('ix_economic_transactions_ledger_id', 'economic_transactions', ['ledger_id'])
    op.create_index('ix_economic_transactions_entity_type', 'economic_transactions', ['entity_type'])
    op.create_index('ix_economic_transactions_entity_id', 'economic_transactions', ['entity_id'])
    op.create_index('ix_economic_transactions_transaction_type', 'economic_transactions', ['transaction_type'])
    op.create_index('ix_economic_transactions_created_at', 'economic_transactions', ['created_at'])
    op.create_index('ix_economic_transactions_entity', 'economic_transactions', ['entity_type', 'entity_id'])
    op.create_index('ix_economic_transactions_type_created', 'economic_transactions', ['transaction_type', 'created_at'])
    
    # Create GIN index for JSONB column for efficient querying
    op.create_index(
        'ix_economic_transactions_resource_details_gin',
        'economic_transactions',
        ['resource_details'],
        postgresql_using='gin'
    )


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('ix_economic_transactions_resource_details_gin', table_name='economic_transactions')
    op.drop_index('ix_economic_transactions_type_created', table_name='economic_transactions')
    op.drop_index('ix_economic_transactions_entity', table_name='economic_transactions')
    op.drop_index('ix_economic_transactions_created_at', table_name='economic_transactions')
    op.drop_index('ix_economic_transactions_transaction_type', table_name='economic_transactions')
    op.drop_index('ix_economic_transactions_entity_id', table_name='economic_transactions')
    op.drop_index('ix_economic_transactions_entity_type', table_name='economic_transactions')
    op.drop_index('ix_economic_transactions_ledger_id', table_name='economic_transactions')
    
    op.drop_index('ix_economic_ledgers_created_at', table_name='economic_ledgers')
    op.drop_index('ix_economic_ledgers_entity', table_name='economic_ledgers')
    op.drop_index('ix_economic_ledgers_entity_id', table_name='economic_ledgers')
    op.drop_index('ix_economic_ledgers_entity_type', table_name='economic_ledgers')
    
    # Drop tables
    op.drop_table('economic_transactions')
    op.drop_table('economic_ledgers')
