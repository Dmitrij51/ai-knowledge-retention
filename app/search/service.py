from app.ai.embeddings import EmbeddingModel
from app.models.chunk import Chunk
from app.search.hybrid import HybridSearch
from app.search.semantic import SemanticSearch


class SearchService:
    """
    Единая точка входа для поиска по базе знаний.

    Остальной код проекта не должен напрямую
    обращаться к FTS5, SemanticSearch или HybridSearch.
    """

    def __init__(self):
        # Загружаем embedding-модель
        model = EmbeddingModel()

        # Semantic Search
        semantic_search = SemanticSearch(model)

        # Hybrid Search
        self.hybrid_search = HybridSearch(semantic_search)

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[tuple[float, Chunk]]:
        """
        Выполняет hybrid search.

        Возвращает:

            [
                (score, Chunk),
                ...
            ]
        """

        if not query.strip():
            return []

        if limit <= 0:
            raise ValueError("limit должен быть больше 0")

        return self.hybrid_search.search(
            query,
            limit=limit,
        )
