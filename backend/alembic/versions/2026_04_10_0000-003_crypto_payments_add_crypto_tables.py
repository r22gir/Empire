"""add crypto_payments and crypto_ledger tables

Revision ID: 003_crypto_payments
Revises: 002_chat_backup
Create Date: 2026-04-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '003_crypto_payments'
down_revision = '002_chat_backup'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'crypto_payments',
        sa.Column('id', sa.String(length=100), primary_key=True),
        sa.Column('order_id', sa.String(length=100), nullable=False, index=True),
        sa.Column('chain', sa.String(length=20), nullable=False),
        sa.Column('token', sa.String(length=20), nullable=False),
        sa.Column('wallet_address', sa.String(length=100), nullable=False),
        sa.Column('expected_amount', sa.Numeric(precision=30, scale=9), nullable=False),
        sa.Column('received_amount', sa.Numeric(precision=30, scale=9), nullable=True),
        sa.Column('tx_hash', sa.String(length=200), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('discount_pct', sa.SmallInteger(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
    )

    op.create_index('ix_crypto_payments_order_id', 'crypto_payments', ['order_id'])
    op.create_index('ix_crypto_payments_status', 'crypto_payments', ['status'])
    op.create_index('ix_crypto_payments_created_at', 'crypto_payments', ['created_at'])

    op.create_table(
        'crypto_ledger',
        sa.Column('id', sa.String(length=100), primary_key=True),
        sa.Column('payment_id', sa.String(length=100), nullable=False, index=True),
        sa.Column('chain', sa.String(length=20), nullable=False),
        sa.Column('token', sa.String(length=20), nullable=False),
        sa.Column('direction', sa.String(length=4), nullable=False),
        sa.Column('amount', sa.Numeric(precision=30, scale=9), nullable=False),
        sa.Column('usd_value', sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column('tx_hash', sa.String(length=200), nullable=False),
        sa.Column('block_number', sa.BigInteger(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )

    op.create_index('ix_crypto_ledger_payment_id', 'crypto_ledger', ['payment_id'])
    op.create_index('ix_crypto_ledger_recorded_at', 'crypto_ledger', ['recorded_at'])


def downgrade() -> None:
    op.drop_index('ix_crypto_ledger_recorded_at', table_name='crypto_ledger')
    op.drop_index('ix_crypto_ledger_payment_id', table_name='crypto_ledger')
    op.drop_table('crypto_ledger')

    op.drop_index('ix_crypto_payments_created_at', table_name='crypto_payments')
    op.drop_index('ix_crypto_payments_status', table_name='crypto_payments')
    op.drop_index('ix_crypto_payments_order_id', table_name='crypto_payments')
    op.drop_table('crypto_payments')
