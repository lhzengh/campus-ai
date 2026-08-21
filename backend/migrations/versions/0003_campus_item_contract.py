"""Align stored messages with the canonical CampusItem v1 contract."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("item_type", sa.String(30), nullable=False, server_default="announcement"),
    )
    op.add_column("messages", sa.Column("content_html", sa.Text(), nullable=True))
    op.add_column("messages", sa.Column("publisher", sa.JSON(), nullable=True))
    op.add_column("messages", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "messages",
        sa.Column("attachments", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "messages",
        sa.Column("extensions", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    # Preserve legacy metadata without interpreting Connector-specific keys.
    op.execute("UPDATE messages SET extensions = metadata")
    with op.batch_alter_table("messages") as batch_op:
        batch_op.drop_constraint("uq_message_source_hash", type_="unique")
        batch_op.alter_column("url", new_column_name="source_url")
        batch_op.alter_column("body", new_column_name="content_text")
        batch_op.drop_column("metadata")


def downgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.execute("UPDATE messages SET metadata = extensions")
    with op.batch_alter_table("messages") as batch_op:
        batch_op.alter_column("source_url", new_column_name="url")
        batch_op.alter_column("content_text", new_column_name="body")
        batch_op.create_unique_constraint("uq_message_source_hash", ["source_id", "content_hash"])
        batch_op.drop_column("extensions")
        batch_op.drop_column("attachments")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("publisher")
        batch_op.drop_column("content_html")
        batch_op.drop_column("item_type")
