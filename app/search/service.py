from app.ai.embeddings import EmbeddingModel
from app.search.semantic import SemanticSearch
from app.search.fts import search_fts


class SearchService:
    """
    Hybrid Search.

    Использует два независимых способа поиска:

    1. Semantic Search
       Ищет информацию по смыслу.

    2. FTS5
       Ищет точные слова, термины и фрагменты текста.

    Затем результаты объединяются.

    Важный принцип:

    Если semantic search нашёл хороший результат,
    отсутствие результата в FTS5 НЕ должно уничтожать его.
    """

    # ============================================================
    # CONFIGURATION
    # ============================================================

    # Минимальная релевантность результата.

    # Раньше было 0.62.
    #
    # Это было слишком жёстко, потому что semantic-only
    # результат дополнительно умножался на 0.70.
    #
    # Теперь semantic-only сохраняет свой score,
    # поэтому 0.40 является разумным стартовым порогом.
    MIN_HYBRID_SCORE = 0.40

    # Максимальное количество результатов,
    # которое отдаём RAG.
    MAX_RESULTS = 5

    # Вес semantic search,
    # если результат найден обоими способами.
    SEMANTIC_WEIGHT = 0.70

    # Вес FTS5,
    # если результат найден обоими способами.
    FTS_WEIGHT = 0.30

    # Бонус, если оба поиска нашли один и тот же chunk.
    BOTH_SEARCH_BONUS = 0.08

    # ============================================================
    # INIT
    # ============================================================

    def __init__(
        self,
        embedding_model: EmbeddingModel | None = None,
    ):
        self.embedding_model = embedding_model or EmbeddingModel()

        self.semantic_search = SemanticSearch(
            model=self.embedding_model,
        )

    # ============================================================
    # SEARCH
    # ============================================================

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[tuple[float, object]]:
        """
        Выполняет hybrid search.

        Возвращает:

            [
                (score, chunk),
                ...
            ]

        где score находится примерно в диапазоне 0..1.
        """

        # ========================================================
        # 1. VALIDATION
        # ========================================================

        query = query.strip()

        if not query:
            return []

        if limit <= 0:
            raise ValueError("limit должен быть больше 0")

        limit = min(
            limit,
            self.MAX_RESULTS,
        )

        # ========================================================
        # 2. SEMANTIC SEARCH
        # ========================================================

        semantic_results = self.semantic_search.search(
            query=query,
            limit=limit * 3,
        )

        # ========================================================
        # 3. FTS5
        # ========================================================

        fts_results = search_fts(
            query=query,
            limit=limit * 3,
        )

        # ========================================================
        # DEBUG
        # ========================================================

        print()
        print("=" * 80)
        print("HYBRID SEARCH")
        print("=" * 80)

        print()
        print("QUERY:")
        print(query)

        # ========================================================
        # DEBUG — SEMANTIC
        # ========================================================

        print()
        print("-" * 80)
        print("SEMANTIC RESULTS")
        print("-" * 80)

        if not semantic_results:
            print("Ничего не найдено.")

        else:
            for score, chunk in semantic_results:
                print(
                    f"\n"
                    f"chunk_id: {chunk.id}\n"
                    f"score: {float(score):.4f}\n"
                    f"content:\n"
                    f"{chunk.content[:500]}"
                )

        # ========================================================
        # DEBUG — FTS
        # ========================================================

        print()
        print("-" * 80)
        print("FTS5 RESULTS")
        print("-" * 80)

        if not fts_results:
            print("Ничего не найдено.")

        else:
            for score, chunk in fts_results:
                print(
                    f"\n"
                    f"chunk_id: {chunk.id}\n"
                    f"bm25: {float(score):.4f}\n"
                    f"content:\n"
                    f"{chunk.content[:500]}"
                )

        # ========================================================
        # 4. NOTHING FOUND
        # ========================================================

        if not semantic_results and not fts_results:
            print()
            print("RESULT: NOTHING FOUND")

            return []

        # ========================================================
        # 5. SEMANTIC SCORES
        # ========================================================

        semantic_scores: dict[int, float] = {}

        for score, chunk in semantic_results:
            semantic_scores[chunk.id] = float(score)

        # ========================================================
        # 6. FTS SCORES
        # ========================================================

        fts_raw_scores: dict[int, float] = {}

        for score, chunk in fts_results:
            fts_raw_scores[chunk.id] = float(score)

        # ========================================================
        # 7. NORMALIZE FTS5
        # ========================================================

        fts_scores: dict[int, float] = {}

        if fts_raw_scores:
            min_score = min(fts_raw_scores.values())

            max_score = max(fts_raw_scores.values())

            # ----------------------------------------------------
            # Если только один результат,
            # нельзя определить относительное качество.
            # ----------------------------------------------------

            if max_score == min_score:
                for chunk_id in fts_raw_scores:
                    fts_scores[chunk_id] = 0.70

            else:
                score_range = max_score - min_score

                for chunk_id, score in fts_raw_scores.items():
                    normalized = (max_score - score) / score_range

                    normalized = max(
                        0.0,
                        min(
                            1.0,
                            normalized,
                        ),
                    )

                    fts_scores[chunk_id] = normalized

        # ========================================================
        # 8. COLLECT CHUNKS
        # ========================================================

        chunks: dict[int, object] = {}

        for _, chunk in semantic_results:
            chunks[chunk.id] = chunk

        for _, chunk in fts_results:
            chunks[chunk.id] = chunk

        # ========================================================
        # 9. IDS
        # ========================================================

        semantic_ids = set(semantic_scores.keys())

        fts_ids = set(fts_scores.keys())

        # ========================================================
        # 10. HYBRID SCORE
        # ========================================================

        results: list[tuple[float, object]] = []

        for chunk_id, chunk in chunks.items():
            semantic_score = semantic_scores.get(
                chunk_id,
                0.0,
            )

            fts_score = fts_scores.get(
                chunk_id,
                0.0,
            )

            # ====================================================
            # CASE 1
            # Найден обоими поисками
            # ====================================================

            if chunk_id in semantic_ids and chunk_id in fts_ids:
                hybrid_score = (
                    semantic_score * self.SEMANTIC_WEIGHT + fts_score * self.FTS_WEIGHT
                )

                hybrid_score += self.BOTH_SEARCH_BONUS

                search_type = "SEMANTIC + FTS"

            # ====================================================
            # CASE 2
            # Найден только semantic search
            # ====================================================

            elif chunk_id in semantic_ids:
                # Очень важный момент.

                # НЕ делаем:

                # semantic_score * 0.70

                # Потому что FTS просто не обязан
                # находить смысловой запрос.

                hybrid_score = semantic_score

                search_type = "SEMANTIC ONLY"

            # ====================================================
            # CASE 3
            # Найден только FTS
            # ====================================================

            else:
                hybrid_score = fts_score

                search_type = "FTS ONLY"

            # ====================================================
            # Ограничиваем 0..1
            # ====================================================

            hybrid_score = max(
                0.0,
                min(
                    1.0,
                    hybrid_score,
                ),
            )

            # ====================================================
            # DEBUG
            # ====================================================

            print()
            print("-" * 80)
            print("CANDIDATE")
            print("-" * 80)

            print(f"chunk_id: {chunk_id}")

            print(f"search_type: {search_type}")

            print(f"semantic_score: {semantic_score:.4f}")

            print(f"fts_score: {fts_score:.4f}")

            print(f"hybrid_score: {hybrid_score:.4f}")

            print(f"threshold: {self.MIN_HYBRID_SCORE:.4f}")

            # ====================================================
            # Добавляем результат
            # ====================================================

            results.append(
                (
                    hybrid_score,
                    chunk,
                )
            )

        # ========================================================
        # 11. SORT
        # ========================================================

        results.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        # ========================================================
        # 12. FILTER
        # ========================================================

        filtered_results = [
            (score, chunk) for score, chunk in results if score >= self.MIN_HYBRID_SCORE
        ]

        # ========================================================
        # DEBUG — FINAL
        # ========================================================

        print()
        print("=" * 80)
        print("FINAL SEARCH RESULTS")
        print("=" * 80)

        if not filtered_results:
            print("Ни один результат не прошёл порог релевантности.")

        else:
            for score, chunk in filtered_results:
                print(
                    f"\n"
                    f"score: {score:.4f}\n"
                    f"chunk_id: {chunk.id}\n"
                    f"content:\n"
                    f"{chunk.content[:500]}"
                )

        print("=" * 80)
        print()

        # ========================================================
        # 13. RETURN TOP RESULTS
        # ========================================================

        return filtered_results[:limit]
