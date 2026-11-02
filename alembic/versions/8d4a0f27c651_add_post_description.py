"""add description to posts

Revision ID: 8d4a0f27c651
Revises: c4e8a1b27d90
Create Date: 2026-10-31 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "8d4a0f27c651"
down_revision: Union[str, Sequence[str], None] = "c4e8a1b27d90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("posts")}
    if "description" not in columns:
        op.add_column("posts", sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("posts")}
    if "description" in columns:
        op.drop_column("posts", "description")
