from sqlalchemy import select

from app.models.chunk import Chunk
from app.models.chunk_fts import ChunkFTS
from app.storage.database import SessionLocal


def search_fts(
    query: str,
    limit: int = 10,
) -> list[Chunk]:
    """
    Выполняет полнотекстовый поиск через SQLite FTS5.

    Возвращает реальные объекты Chunk.
    """

    if not query.strip():
        return []

    with SessionLocal() as session:
        stmt = (
            select(Chunk)
            .join(
                ChunkFTS,
                Chunk.id == ChunkFTS.rowid,
            )
            .where(ChunkFTS.content.match(query))
            .limit(limit)
        )

        result = session.scalars(stmt)

        return list(result.all())
