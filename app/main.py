from app.search.fts import search_fts


results = search_fts("python")


print(f"Найдено: {len(results)}")

for chunk in results:
    print("\n" + "=" * 50)
    print(f"Chunk ID: {chunk.id}")
    print(f"Document ID: {chunk.document_id}")
    print("=" * 50)
    print(chunk.content)
