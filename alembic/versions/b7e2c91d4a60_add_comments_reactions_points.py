"""add comments, reactions, tasks and points

Revision ID: b7e2c91d4a60
Revises: f18a2c6d9e40
Create Date: 2026-11-04 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
from fastapi_users_db_sqlalchemy.generics import GUID
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "b7e2c91d4a60"
down_revision: Union[str, Sequence[str], None] = "f18a2c6d9e40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The app also creates these on startup, so any of them may already exist.
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    columns = {column["name"] for column in inspector.get_columns("posts")}
    if "comments_disabled" not in columns:
        op.add_column(
            "posts",
            sa.Column("comments_disabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    if "comments" not in tables:
        op.create_table(
            "comments",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column(
                "post_id",
                sa.String(),
                sa.ForeignKey("posts.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("user_id", GUID(), sa.ForeignKey("user.id"), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime()),
        )

    if "post_reactions" not in tables:
        op.create_table(
            "post_reactions",
            sa.Column(
                "post_id",
                sa.String(),
                sa.ForeignKey("posts.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("user_id", GUID(), sa.ForeignKey("user.id"), primary_key=True),
            sa.Column("reaction", sa.String(), nullable=False),
            sa.CheckConstraint("reaction IN ('up', 'down')", name="ck_post_reactions_reaction"),
        )

    if "comment_reactions" not in tables:
        op.create_table(
            "comment_reactions",
            sa.Column(
                "comment_id",
                sa.String(),
                sa.ForeignKey("comments.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("user_id", GUID(), sa.ForeignKey("user.id"), primary_key=True),
            sa.Column("reaction", sa.String(), nullable=False),
            sa.CheckConstraint("reaction IN ('up', 'down')", name="ck_comment_reactions_reaction"),
        )

    if "tasks" not in tables:
        op.create_table(
            "tasks",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("points", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime()),
            sa.CheckConstraint("points > 0", name="ck_tasks_points_positive"),
        )

    if "point_transactions" not in tables:
        op.create_table(
            "point_transactions",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", GUID(), sa.ForeignKey("user.id"), nullable=False, index=True),
            sa.Column("points", sa.Integer(), nullable=False),
            sa.Column("source", sa.String(), nullable=False),
            sa.Column("post_id", sa.String(), sa.ForeignKey("posts.id", ondelete="SET NULL"), index=True),
            sa.Column("comment_id", sa.String(), sa.ForeignKey("comments.id", ondelete="SET NULL"), index=True),
            sa.Column("task_id", sa.String(), sa.ForeignKey("tasks.id", ondelete="SET NULL")),
            sa.Column("awarded_by", GUID(), sa.ForeignKey("user.id")),
            sa.Column("created_at", sa.DateTime()),
            sa.CheckConstraint("points > 0", name="ck_point_transactions_points_positive"),
            sa.UniqueConstraint("user_id", "task_id", name="uq_point_transactions_user_task"),
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    for table in (
        "point_transactions",
        "tasks",
        "comment_reactions",
        "post_reactions",
        "comments",
    ):
        if table in tables:
            op.drop_table(table)

    columns = {column["name"] for column in inspector.get_columns("posts")}
    if "comments_disabled" in columns:
        with op.batch_alter_table("posts") as batch_op:
            batch_op.drop_column("comments_disabled")