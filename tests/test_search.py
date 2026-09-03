from app.search.service import SearchService


def main():
    service = SearchService()

    queries = [
        "Docker Compose",
        "как запускать несколько сервисов",
        "контейнеры",
    ]

    for query in queries:
        print("\n" + "=" * 70)
        print(f"ЗАПРОС: {query}")
        print("=" * 70)

        results = service.search(
            query,
            limit=5,
        )

        if not results:
            print("Ничего не найдено.")
            continue

        for index, (score, chunk) in enumerate(results, start=1):
            print(f"\n[{index}] Score: {score:.4f}")
            print(f"Chunk ID: {chunk.id}")
            print(f"Document ID: {chunk.document_id}")
            print("-" * 50)
            print(chunk.content[:500])


if __name__ == "__main__":
    main()
