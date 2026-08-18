"""add document soft delete

Revision ID: ad8419980e79
Revises: d9662e771c8c
Create Date: 2026-08-18 19:22:31.521746

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ad8419980e79"
down_revision: Union[str, Sequence[str], None] = "d9662e771c8c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавляет признак удаления документа."""

    op.add_column(
        "documents",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    """Удаляет признак удаления документа."""

    op.drop_column(
        "documents",
        "is_deleted",
    )
