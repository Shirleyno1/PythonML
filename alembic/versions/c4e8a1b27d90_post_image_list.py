"""move post files onto an image list

Revision ID: c4e8a1b27d90
Revises: 362731dd67e5
Create Date: 2026-10-31 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

from posts.db import migrate_legacy_posts

revision: str = "c4e8a1b27d90"
down_revision: Union[str, Sequence[str], None] = "362731dd67e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    migrate_legacy_posts(op.get_bind())


def downgrade() -> None:
    raise NotImplementedError(
        "A post can hold many images, so this change cannot be reversed automatically."
    )
