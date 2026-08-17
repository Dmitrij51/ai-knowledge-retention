from app.models.chunk import Chunk
from app.search.fts import search_fts


def search(query: str, limit: int = 10) -> list[Chunk]:
    """
    Основная точка входа для поиска по базе знаний.
    """

    if not query.strip():
        return []

    return search_fts(query, limit=limit)
