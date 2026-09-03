"""add unique document version

Revision ID: e4d232af7653
Revises: ad8419980e79
Create Date: 2026-08-21 11:21:28.247588
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e4d232af7653"
down_revision: Union[str, Sequence[str], None] = "ad8419980e79"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Добавляет уникальность пары: document_id + version

    FTS5-таблицы не трогаем.
    """
    with op.batch_alter_table("file_versions") as batch_op:
        batch_op.create_unique_constraint(
            "uq_file_versions_document_version",
            ["document_id", "version"],
        )


def downgrade() -> None:
    """
    Удаляет ограничение уникальности.
    """
    with op.batch_alter_table("file_versions") as batch_op:
        batch_op.drop_constraint(
            "uq_file_versions_document_version",
            type_="unique",
        )
