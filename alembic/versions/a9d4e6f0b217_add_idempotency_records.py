"""add idempotency records

Revision ID: a9d4e6f0b217
Revises: c3f1a7d82b54
Create Date: 2026-11-05 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
from fastapi_users_db_sqlalchemy.generics import GUID
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "a9d4e6f0b217"
down_revision: Union[str, Sequence[str], None] = "c3f1a7d82b54"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The app also creates this on startup, so it may already exist.
    if "idempotency_records" in inspect(op.get_bind()).get_table_names():
        return

    op.create_table(
        "idempotency_records",
        sa.Column(
            "user_id",
            GUID(),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("key", sa.String(length=255), primary_key=True),
        sa.Column("fingerprint", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("response_status", sa.Integer()),
        sa.Column("response_body", sa.JSON()),
        sa.Column("locked_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table("idempotency_records")
