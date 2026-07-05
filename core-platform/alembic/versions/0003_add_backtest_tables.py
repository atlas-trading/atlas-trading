"""add backtest result tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-06
"""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("initial_balance", sa.Numeric(20, 8), nullable=False),
        sa.Column("final_balance", sa.Numeric(20, 8), nullable=False),
        sa.Column("order_qty", sa.Numeric(20, 8), nullable=False),
        sa.Column("min_profit", sa.Numeric(20, 8), nullable=False),
        sa.Column("slippage", sa.Numeric(20, 8), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "backtest_trades",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Integer, sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("arb_id", sa.String(100), nullable=False),
        sa.Column("leg1_pair", sa.String(20), nullable=False),
        sa.Column("leg2_pair", sa.String(20), nullable=False),
        sa.Column("leg3_pair", sa.String(20), nullable=False),
        sa.Column("expected_profit", sa.Numeric(20, 8), nullable=False),
        sa.Column("actual_profit", sa.Numeric(20, 8), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
    )
    op.create_index("ix_backtest_trades_run_id", "backtest_trades", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_backtest_trades_run_id", table_name="backtest_trades")
    op.drop_table("backtest_trades")
    op.drop_table("backtest_runs")
