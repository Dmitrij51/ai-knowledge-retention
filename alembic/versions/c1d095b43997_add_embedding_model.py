"""add embedding model

Revision ID: c1d095b43997
Revises: 19d25482e720
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1d095b43997"
down_revision: Union[str, Sequence[str], None] = "19d25482e720"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chunks",
        sa.Column(
            "embedding_model",
            sa.Text(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "chunks",
        "embedding_model",
    )
