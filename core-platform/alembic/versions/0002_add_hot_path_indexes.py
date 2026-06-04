"""add hot-path indexes

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-04

H-5: arb_attempts.created_at, arb_attempts.status, and raw_ticks (symbol,
timestamp) are the columns the dashboard and analytics queries filter on
constantly. Without indexes those queries are full-table scans even on
modest data volumes.
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_arb_attempts_created_at",
        "arb_attempts",
        ["created_at"],
    )
    op.create_index(
        "ix_arb_attempts_status",
        "arb_attempts",
        ["status"],
    )
    op.create_index(
        "ix_raw_ticks_symbol_ts",
        "raw_ticks",
        ["symbol", "timestamp"],
    )


def downgrade() -> None:
    op.drop_index("ix_raw_ticks_symbol_ts", table_name="raw_ticks")
    op.drop_index("ix_arb_attempts_status", table_name="arb_attempts")
    op.drop_index("ix_arb_attempts_created_at", table_name="arb_attempts")
