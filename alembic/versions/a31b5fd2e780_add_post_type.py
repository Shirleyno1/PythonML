"""add type to posts

Revision ID: a31b5fd2e780
Revises: 8d4a0f27c651
Create Date: 2026-11-01 15:58:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "a31b5fd2e780"
down_revision: Union[str, Sequence[str], None] = "8d4a0f27c651"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("posts")}
    if "type" not in columns:
        op.add_column(
            "posts",
            sa.Column("type", sa.String(), nullable=False, server_default="share"),
        )


def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("posts")}
    if "type" in columns:
        op.drop_column("posts", "type")
