import re

from sqlalchemy import select, text

from app.models.chunk import Chunk
from app.storage.database import SessionLocal


def _prepare_fts_query(query: str) -> str:
    """
    Подготавливает запрос для SQLite FTS5.

    Например:
        docker CMD

    превращается в:
        "docker"* "CMD"*
    """

    tokens = re.findall(
        r"\w+",
        query.replace('"', " "),
        flags=re.UNICODE,
    )

    if not tokens:
        return ""

    return " ".join(f'"{token}"*' for token in tokens)


def search_fts(
    query: str,
    limit: int = 10,
) -> list[tuple[float, Chunk]]:
    """
    Полнотекстовый поиск через SQLite FTS5.

    Возвращает:
        (BM25 score, Chunk)

    В SQLite FTS5:
        меньше score = более релевантный результат.
    """

    if not query.strip():
        return []

    if limit <= 0:
        raise ValueError("limit должен быть больше 0")

    fts_query = _prepare_fts_query(query)

    if not fts_query:
        return []

    with SessionLocal() as session:
        # 1. Получаем ID chunks и BM25 score из FTS5
        fts_stmt = text(
            """
            SELECT
                rowid,
                bm25(chunks_fts) AS score
            FROM chunks_fts
            WHERE chunks_fts MATCH :query
            ORDER BY score ASC
            LIMIT :limit
            """
        )

        fts_rows = session.execute(
            fts_stmt,
            {
                "query": fts_query,
                "limit": limit,
            },
        ).all()

        if not fts_rows:
            return []

        # Сохраняем порядок FTS5
        scores = {int(rowid): float(score) for rowid, score in fts_rows}

        chunk_ids = list(scores.keys())

        # 2. Получаем реальные ORM Chunk
        chunks_stmt = select(Chunk).where(Chunk.id.in_(chunk_ids))

        chunks = session.scalars(chunks_stmt).all()

        chunks_by_id = {chunk.id: chunk for chunk in chunks}

        # 3. Восстанавливаем порядок FTS5
        results = []

        for chunk_id in chunk_ids:
            chunk = chunks_by_id.get(chunk_id)

            if chunk is not None:
                results.append(
                    (
                        scores[chunk_id],
                        chunk,
                    )
                )

        return results
