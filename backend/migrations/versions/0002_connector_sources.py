"""Replace Core-owned source kinds with Connector instance fields."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add nullable identity first so existing validation rows can be backfilled.
    op.add_column("sources", sa.Column("connector_id", sa.String(200), nullable=True))
    op.add_column("sources", sa.Column("connector_version", sa.String(50), nullable=True))
    op.add_column("sources", sa.Column("credential_refs", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.add_column("sources", sa.Column("sync_cursor", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.add_column("sources", sa.Column("auth_status", sa.String(30), nullable=False, server_default="unknown"))
    op.add_column("sources", sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("sources", sa.Column("last_error", sa.Text(), nullable=True))
    op.execute("UPDATE sources SET connector_id = kind")
    # Batch mode keeps the migration portable to SQLite-based local validation.
    with op.batch_alter_table("sources") as batch_op:
        batch_op.alter_column("connector_id", nullable=False)
        batch_op.drop_column("kind")
    op.create_index("ix_sources_connector_id", "sources", ["connector_id"])


def downgrade() -> None:
    op.add_column("sources", sa.Column("kind", sa.String(50), nullable=True))
    op.execute("UPDATE sources SET kind = connector_id")
    op.drop_index("ix_sources_connector_id", table_name="sources")
    with op.batch_alter_table("sources") as batch_op:
        batch_op.alter_column("kind", nullable=False)
        batch_op.drop_column("last_error")
        batch_op.drop_column("last_success_at")
        batch_op.drop_column("auth_status")
        batch_op.drop_column("sync_cursor")
        batch_op.drop_column("credential_refs")
        batch_op.drop_column("connector_version")
        batch_op.drop_column("connector_id")
