"""add chunks fts5

Revision ID: 852e9ecfa992
Revises: 8a66c5839b77
Create Date: 2026-08-16 21:02:23.660048

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '852e9ecfa992'
down_revision: Union[str, Sequence[str], None] = '8a66c5839b77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаём FTS5 virtual table
    op.execute(
        """
        CREATE VIRTUAL TABLE chunks_fts
        USING fts5(
            content,
            content='chunks',
            content_rowid='id'
        )
        """
    )

    # Индексируем chunks, которые уже существуют
    op.execute(
        """
        INSERT INTO chunks_fts(rowid, content)
        SELECT id, content
        FROM chunks
        """
    )

    # Новый Chunk → FTS5
    op.execute(
        """
        CREATE TRIGGER chunks_ai
        AFTER INSERT ON chunks
        BEGIN
            INSERT INTO chunks_fts(
                rowid,
                content
            )
            VALUES (
                new.id,
                new.content
            );
        END;
        """
    )

    # Удалённый Chunk → удалить из FTS5
    op.execute(
        """
        CREATE TRIGGER chunks_ad
        AFTER DELETE ON chunks
        BEGIN
            INSERT INTO chunks_fts(
                chunks_fts,
                rowid,
                content
            )
            VALUES (
                'delete',
                old.id,
                old.content
            );
        END;
        """
    )

    # Изменённый Chunk → обновить FTS5
    op.execute(
        """
        CREATE TRIGGER chunks_au
        AFTER UPDATE OF content ON chunks
        BEGIN
            INSERT INTO chunks_fts(
                chunks_fts,
                rowid,
                content
            )
            VALUES (
                'delete',
                old.id,
                old.content
            );

            INSERT INTO chunks_fts(
                rowid,
                content
            )
            VALUES (
                new.id,
                new.content
            );
        END;
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS chunks_au")

    op.execute("DROP TRIGGER IF EXISTS chunks_ad")

    op.execute("DROP TRIGGER IF EXISTS chunks_ai")

    op.execute("DROP TABLE IF EXISTS chunks_fts")