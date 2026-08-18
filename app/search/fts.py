import re

from sqlalchemy import select, text

from app.models.chunk import Chunk
from app.models.document import Document
from app.storage.database import SessionLocal


MIN_CHUNK_LENGTH = 20


def _prepare_fts_query(query: str) -> str:
    """
    Подготавливает пользовательский запрос
    для SQLite FTS5.

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
        меньше score = лучше результат.
    """

    if not query.strip():
        return []

    if limit <= 0:
        raise ValueError("limit должен быть больше 0")

    fts_query = _prepare_fts_query(query)

    if not fts_query:
        return []

    with SessionLocal() as session:
        # ---------------------------------
        # 1. Поиск через FTS5
        # ---------------------------------

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

        scores = {int(rowid): float(score) for rowid, score in fts_rows}

        chunk_ids = list(scores.keys())

        # ---------------------------------
        # 2. Получаем chunks
        #    только активных документов
        # ---------------------------------

        chunks_stmt = (
            select(Chunk)
            .join(
                Document,
                Chunk.document_id == Document.id,
            )
            .where(
                Chunk.id.in_(chunk_ids),
                Document.is_deleted.is_(False),
            )
        )

        chunks = session.scalars(chunks_stmt).all()

        chunks_by_id = {
            chunk.id: chunk
            for chunk in chunks
            if chunk.content and len(chunk.content.strip()) >= MIN_CHUNK_LENGTH
        }

        # ---------------------------------
        # 3. Восстанавливаем порядок FTS5
        # ---------------------------------

        results = []

        for chunk_id in chunk_ids:
            chunk = chunks_by_id.get(chunk_id)

            if chunk is None:
                continue

            results.append(
                (
                    scores[chunk_id],
                    chunk,
                )
            )

        return results
