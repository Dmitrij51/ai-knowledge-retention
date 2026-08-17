from sqlalchemy import select

from app.ai.embeddings import EmbeddingModel
from app.ai.vector import embedding_to_bytes
from app.models.document import Document
from app.models.chunk import Chunk
from app.storage.database import SessionLocal


def main():
    model = EmbeddingModel()

    with SessionLocal() as session:
        chunk = session.scalar(select(Chunk).limit(1))

        if chunk is None:
            print("Chunks не найдены")
            return

        embedding = model.embed_document(chunk.content)

        chunk.embedding = embedding_to_bytes(embedding)

        session.commit()

        print(f"Chunk ID: {chunk.id}")
        print(f"Embedding размер: {len(embedding)}")
        print(f"Embedding bytes: {len(chunk.embedding)}")


if __name__ == "__main__":
    main()
