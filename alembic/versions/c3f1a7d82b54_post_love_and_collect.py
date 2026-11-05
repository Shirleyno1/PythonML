"""replace thumbs on posts with love and collect

Revision ID: c3f1a7d82b54
Revises: b7e2c91d4a60
Create Date: 2026-11-04 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
from fastapi_users_db_sqlalchemy.generics import GUID
import sqlalchemy as sa

from posts.db import migrate_post_reactions

revision: str = "c3f1a7d82b54"
down_revision: Union[str, Sequence[str], None] = "b7e2c91d4a60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    migrate_post_reactions(op.get_bind())


def downgrade() -> None:
    # Love and collect have no thumb equivalent, so their rows aren't kept.
    op.drop_table("post_reactions")
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
