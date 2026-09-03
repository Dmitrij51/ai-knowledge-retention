"""add document file hash

Revision ID: 96094bcf8610
Revises: c1d095b43997
Create Date: 2026-08-17 22:50:22.826154

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "96094bcf8610"
down_revision: Union[str, Sequence[str], None] = "c1d095b43997"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column(
        "documents",
        sa.Column(
            "file_hash",
            sa.String(length=64),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_column(
        "documents",
        "file_hash",
    )
