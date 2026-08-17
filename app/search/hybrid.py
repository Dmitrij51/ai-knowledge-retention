from app.search.fts import search_fts
from app.search.semantic import SemanticSearch
from app.models.chunk import Chunk


class HybridSearch:
    """
    Комбинированный поиск:
    FTS5 + Semantic Search.
    """

    def __init__(
        self,
        semantic_search: SemanticSearch,
    ):
        self.semantic_search = semantic_search

    def search(
        self,
        query: str,
        limit: int = 5,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ) -> list[tuple[float, Chunk]]:

        if not query.strip():
            return []

        if limit <= 0:
            raise ValueError("limit должен быть больше 0")

        if semantic_weight < 0 or keyword_weight < 0:
            raise ValueError("Вес поиска не может быть отрицательным")

        total_weight = semantic_weight + keyword_weight

        if total_weight == 0:
            raise ValueError("Сумма весов должна быть больше 0")

        # Нормализуем веса
        semantic_weight /= total_weight
        keyword_weight /= total_weight

        # -------------------------
        # 1. Semantic Search
        # -------------------------

        semantic_results = self.semantic_search.search(
            query,
            limit=limit * 3,
        )

        semantic_scores = {chunk.id: score for score, chunk in semantic_results}

        chunks = {chunk.id: chunk for _, chunk in semantic_results}

        # -------------------------
        # 2. FTS5
        # -------------------------

        keyword_results = search_fts(
            query,
            limit=limit * 3,
        )

        keyword_scores = {}

        total_keyword = len(keyword_results)

        for index, (fts_score, chunk) in enumerate(keyword_results):
            if total_keyword == 1:
                score = 1.0
            else:
                score = 1.0 - (index / total_keyword)

            keyword_scores[chunk.id] = score
            chunks[chunk.id] = chunk

        # -------------------------
        # 3. Объединяем результаты
        # -------------------------

        results = []

        for chunk_id, chunk in chunks.items():
            semantic_score = semantic_scores.get(
                chunk_id,
                0.0,
            )

            keyword_score = keyword_scores.get(
                chunk_id,
                0.0,
            )

            final_score = (
                semantic_score * semantic_weight + keyword_score * keyword_weight
            )

            results.append((final_score, chunk))

        # -------------------------
        # 4. Сортировка
        # -------------------------

        results.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return results[:limit]
