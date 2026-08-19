from app.ai.embeddings import EmbeddingModel
from app.search.semantic import SemanticSearch
from app.search.fts import search_fts


class SearchService:
    """
    Hybrid search.

    Использует одновременно:

    1. Semantic Search
       Ищет информацию по смыслу.

    2. FTS5
       Ищет точные совпадения слов и терминов.

    Затем результаты объединяются в единый hybrid score.
    """

    # Минимальный итоговый score результата.
    #
    # Если результат слабее этого значения,
    # он не передаётся дальше в RAG.
    MIN_HYBRID_SCORE = 0.62

    # Максимальное количество результатов.
    MAX_RESULTS = 3

    # Вес semantic search.
    SEMANTIC_WEIGHT = 0.70

    # Вес FTS5.
    FTS_WEIGHT = 0.30

    # Дополнительный бонус, если chunk найден
    # одновременно semantic search и FTS5.
    BOTH_SEARCH_BONUS = 0.08

    def __init__(
        self,
        embedding_model: EmbeddingModel | None = None,
    ):
        self.embedding_model = embedding_model or EmbeddingModel()

        self.semantic_search = SemanticSearch(
            model=self.embedding_model,
        )

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[tuple[float, object]]:
        """
        Выполняет hybrid search.

        Используются одновременно:

        - semantic search;
        - FTS5.

        Результаты объединяются и ранжируются.

        Возвращает:

            [
                (hybrid_score, chunk),
                ...
            ]
        """

        if not query.strip():
            return []

        if limit <= 0:
            raise ValueError("limit должен быть больше 0")

        limit = min(limit, self.MAX_RESULTS)

        # =================================================
        # 1. Semantic Search
        # =================================================

        semantic_results = self.semantic_search.search(
            query=query,
            limit=limit * 3,
        )

        # =================================================
        # 2. FTS5
        # =================================================

        fts_results = search_fts(
            query=query,
            limit=limit * 3,
        )

        # Если оба поиска ничего не нашли —
        # сразу возвращаем пустой список.
        if not semantic_results and not fts_results:
            return []

        # =================================================
        # 3. Semantic scores
        # =================================================

        semantic_scores: dict[int, float] = {}

        for score, chunk in semantic_results:
            semantic_scores[chunk.id] = float(score)

        # =================================================
        # 4. FTS scores
        # =================================================

        fts_raw_scores: dict[int, float] = {}

        for score, chunk in fts_results:
            fts_raw_scores[chunk.id] = float(score)

        # -------------------------------------------------
        # Нормализуем FTS BM25.
        #
        # В SQLite FTS5:
        #
        # меньше score = лучше.
        #
        # Преобразуем результат в диапазон 0..1,
        # где 1 = лучший результат.
        # -------------------------------------------------

        fts_scores: dict[int, float] = {}

        if fts_raw_scores:
            min_score = min(fts_raw_scores.values())
            max_score = max(fts_raw_scores.values())

            if max_score == min_score:
                # Если найден только один результат
                # или все scores одинаковые.
                #
                # Не считаем его автоматически идеальным.
                for chunk_id in fts_raw_scores:
                    fts_scores[chunk_id] = 0.70

            else:
                score_range = max_score - min_score

                for chunk_id, score in fts_raw_scores.items():
                    normalized = (max_score - score) / score_range

                    # Ограничиваем диапазон 0..1.
                    normalized = max(
                        0.0,
                        min(1.0, normalized),
                    )

                    fts_scores[chunk_id] = normalized

        # =================================================
        # 5. Собираем все chunks
        # =================================================

        chunks: dict[int, object] = {}

        for _, chunk in semantic_results:
            chunks[chunk.id] = chunk

        for _, chunk in fts_results:
            chunks[chunk.id] = chunk

        # =================================================
        # 6. Вычисляем hybrid score
        # =================================================

        results: list[tuple[float, object]] = []

        semantic_ids = set(semantic_scores.keys())
        fts_ids = set(fts_scores.keys())

        for chunk_id, chunk in chunks.items():
            semantic_score = semantic_scores.get(
                chunk_id,
                0.0,
            )

            fts_score = fts_scores.get(
                chunk_id,
                0.0,
            )

            # -------------------------------------------------
            # Базовый hybrid score
            # -------------------------------------------------

            hybrid_score = (
                semantic_score * self.SEMANTIC_WEIGHT + fts_score * self.FTS_WEIGHT
            )

            # -------------------------------------------------
            # Бонус за подтверждение двумя поисками
            # -------------------------------------------------
            #
            # Если chunk найден и semantic search,
            # и FTS5 — это более надёжный кандидат.
            #
            # Например:
            #
            # "docker compose up"
            #
            # Semantic -> найден
            # FTS      -> найден
            #
            # Такой результат получает небольшой бонус.
            # -------------------------------------------------

            if chunk_id in semantic_ids and chunk_id in fts_ids:
                hybrid_score += self.BOTH_SEARCH_BONUS

            # -------------------------------------------------
            # Ограничиваем score диапазоном 0..1
            # -------------------------------------------------

            hybrid_score = max(
                0.0,
                min(1.0, hybrid_score),
            )

            results.append(
                (
                    hybrid_score,
                    chunk,
                )
            )

        # =================================================
        # 7. Сортируем
        # =================================================

        results.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        # =================================================
        # 8. Убираем слабые результаты
        # =================================================

        results = [
            (score, chunk) for score, chunk in results if score >= self.MIN_HYBRID_SCORE
        ]

        # =================================================
        # 9. Возвращаем лучшие результаты
        # =================================================

        return results[:limit]
