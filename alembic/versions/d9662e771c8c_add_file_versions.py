"""add file versions

Revision ID: d9662e771c8c
Revises: f32947ee081c
Create Date: 2026-08-18 16:07:38.339926

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d9662e771c8c"
down_revision: Union[str, Sequence[str], None] = "f32947ee081c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Создаёт таблицу истории версий файлов.
    """

    op.create_table(
        "file_versions",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "document_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "file_hash",
            sa.String(length=64),
            nullable=False,
        ),

        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
        ),

        sa.Column(
            "embedding",
            sa.LargeBinary(),
            nullable=True,
        ),

        sa.Column(
            "embedding_model",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_file_versions_document_id",
        "file_versions",
        ["document_id"],
        unique=False,
    )


def downgrade() -> None:
    """
    Удаляет таблицу истории версий файлов.
    """

    op.drop_index(
        "ix_file_versions_document_id",
        table_name="file_versions",
    )

    op.drop_table("file_versions")

