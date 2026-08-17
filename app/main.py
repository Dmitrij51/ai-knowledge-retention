from app.ai.embeddings import EmbeddingModel
from app.search.semantic import SemanticSearch
from app.search.hybrid import HybridSearch


def main():

    # Загружаем модель E5
    model = EmbeddingModel()

    # Создаём Semantic Search
    semantic_search = SemanticSearch(model)

    # Создаём Hybrid Search
    hybrid_search = HybridSearch(semantic_search)

    query = "LLM"

    results = hybrid_search.search(
        query,
        limit=5,
    )

    print(f"\nЗапрос: {query}")
    print(f"Найдено: {len(results)}\n")

    for score, chunk in results:
        print(f"Score: {score:.4f}")
        print(f"Chunk ID: {chunk.id}")
        print(chunk.content)
        print("-" * 60)


if __name__ == "__main__":
    main()
