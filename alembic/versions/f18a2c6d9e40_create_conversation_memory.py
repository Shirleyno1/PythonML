"""create conversation memory tables

Revision ID: f18a2c6d9e40
Revises: d6c73a8f4b21
Create Date: 2026-11-02 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f18a2c6d9e40"
down_revision: Union[str, Sequence[str], None] = "d6c73a8f4b21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "conversations" not in tables:
        op.create_table(
            "conversations",
            sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
            sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    tables = set(sa.inspect(bind).get_table_names())
    if "conversation_messages" not in tables:
        op.create_table(
            "conversation_messages",
            sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
            sa.Column("conversation_id", sa.Uuid(as_uuid=True), nullable=False),
            sa.Column("role", sa.String(length=20), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["conversation_id"],
                ["conversations.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    inspector = sa.inspect(bind)
    conversation_indexes = {
        index["name"] for index in inspector.get_indexes("conversations")
    }
    if "ix_conversations_user_id" not in conversation_indexes:
        op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    message_indexes = {
        index["name"] for index in inspector.get_indexes("conversation_messages")
    }
    if "ix_conversation_messages_conversation_id" not in message_indexes:
        op.create_index(
            "ix_conversation_messages_conversation_id",
            "conversation_messages",
            ["conversation_id"],
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "conversation_messages" in tables:
        indexes = {
            index["name"]
            for index in inspector.get_indexes("conversation_messages")
        }
        if "ix_conversation_messages_conversation_id" in indexes:
            op.drop_index(
                "ix_conversation_messages_conversation_id",
                table_name="conversation_messages",
            )
        op.drop_table("conversation_messages")

    if "conversations" in tables:
        indexes = {
            index["name"] for index in inspector.get_indexes("conversations")
        }
        if "ix_conversations_user_id" in indexes:
            op.drop_index("ix_conversations_user_id", table_name="conversations")
        op.drop_table("conversations")
