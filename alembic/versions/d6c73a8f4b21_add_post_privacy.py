"""add privacy flag to posts

Revision ID: d6c73a8f4b21
Revises: a31b5fd2e780
Create Date: 2026-11-01 20:08:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "d6c73a8f4b21"
down_revision: Union[str, Sequence[str], None] = "a31b5fd2e780"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("posts")}
    if "isPrivate" not in columns:
        op.add_column(
            "posts",
            sa.Column("isPrivate", sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("posts")}
    if "isPrivate" in columns:
        op.drop_column("posts", "isPrivate")
