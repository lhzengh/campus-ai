"""Add source lifecycle, per-source scheduling, and job diagnostics."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sources",
        sa.Column("schedule_mode", sa.String(20), nullable=False, server_default="daily"),
    )
    op.add_column(
        "sources",
        sa.Column("schedule_time", sa.Time(), nullable=False, server_default="07:00:00"),
    )
    op.add_column(
        "sources",
        sa.Column("schedule_timezone", sa.String(100), nullable=False, server_default="Asia/Shanghai"),
    )
    op.add_column("sources", sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("sources", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_sources_schedule_due", "sources", ["schedule_mode", "enabled", "next_run_at"])

    op.add_column("jobs", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("result", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))


def downgrade() -> None:
    op.drop_column("jobs", "result")
    op.drop_column("jobs", "finished_at")
    op.drop_column("jobs", "started_at")

    op.drop_index("ix_sources_schedule_due", table_name="sources")
    op.drop_column("sources", "archived_at")
    op.drop_column("sources", "next_run_at")
    op.drop_column("sources", "schedule_timezone")
    op.drop_column("sources", "schedule_time")
    op.drop_column("sources", "schedule_mode")
