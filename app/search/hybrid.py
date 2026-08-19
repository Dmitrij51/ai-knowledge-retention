from app.models.chunk import Chunk
from app.search.fts import search_fts
from app.search.semantic import SemanticSearch


class HybridSearch:
    """
    Комбинированный поиск:

    Semantic Search + FTS5.

    Чем выше итоговый score,
    тем более релевантен chunk.
    """

    def __init__(
        self,
        semantic_search: SemanticSearch,
    ):
        self.semantic_search = semantic_search

    @staticmethod
    def _normalize_semantic_scores(
        results: list[tuple[float, Chunk]],
    ) -> dict[int, float]:
        """
        Приводит cosine similarity из [-1, 1]
        к диапазону [0, 1].
        """

        normalized = {}

        for score, chunk in results:
            score = max(-1.0, min(1.0, score))
            normalized[chunk.id] = (score + 1.0) / 2.0

        return normalized

    @staticmethod
    def _normalize_keyword_scores(
        results: list[tuple[float, Chunk]],
    ) -> dict[int, float]:
        """
        SQLite FTS5 BM25:

        меньше score = лучше результат.

        Преобразуем в:

        больше score = лучше результат.
        """

        if not results:
            return {}

        scores = [score for score, _ in results]

        min_score = min(scores)
        max_score = max(scores)

        if max_score == min_score:
            return {chunk.id: 1.0 for _, chunk in results}

        return {
            chunk.id: ((max_score - score) / (max_score - min_score))
            for score, chunk in results
        }

    def search(
        self,
        query: str,
        limit: int = 5,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        min_score: float = 0.55,
    ) -> list[tuple[float, Chunk]]:
        """
        Выполняет hybrid search.

        Дополнительно удаляет слишком слабые результаты
        по итоговому score.

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

        if semantic_weight < 0:
            raise ValueError("semantic_weight не может быть отрицательным")

        if keyword_weight < 0:
            raise ValueError("keyword_weight не может быть отрицательным")

        if not 0 <= min_score <= 1:
            raise ValueError("min_score должен находиться между 0 и 1")

        total_weight = semantic_weight + keyword_weight

        if total_weight == 0:
            raise ValueError("Сумма весов должна быть больше 0")

        semantic_weight /= total_weight
        keyword_weight /= total_weight

        # Ищем больше результатов,
        # чтобы после фильтрации остались хорошие.
        search_limit = max(
            limit * 4,
            20,
        )

        # ---------------------------------
        # 1. Semantic Search
        # ---------------------------------

        semantic_results = self.semantic_search.search(
            query,
            limit=search_limit,
        )

        semantic_scores = self._normalize_semantic_scores(semantic_results)

        chunks = {chunk.id: chunk for _, chunk in semantic_results}

        # ---------------------------------
        # 2. FTS5
        # ---------------------------------

        keyword_results = search_fts(
            query,
            limit=search_limit,
        )

        keyword_scores = self._normalize_keyword_scores(keyword_results)

        for _, chunk in keyword_results:
            chunks[chunk.id] = chunk

        # ---------------------------------
        # 3. Объединяем результаты
        # ---------------------------------

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

            has_semantic = chunk_id in semantic_scores

            has_keyword = chunk_id in keyword_scores

            if has_semantic and has_keyword:
                final_score = (
                    semantic_score * semantic_weight + keyword_score * keyword_weight
                )

            elif has_keyword:
                final_score = keyword_score

            elif has_semantic:
                final_score = semantic_score

            else:
                continue

            # ---------------------------------
            # Фильтрация слабых результатов
            # ---------------------------------

            if final_score < min_score:
                continue

            results.append(
                (
                    final_score,
                    chunk,
                )
            )

        # ---------------------------------
        # 4. Сортировка
        # ---------------------------------

        results.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return results[:limit]
