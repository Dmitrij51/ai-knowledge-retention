from sqlalchemy import select

from app.ai.embeddings import EmbeddingModel
from app.models.chunk import Chunk
from app.models.document import Document
from app.services.embeddings import EmbeddingService
from app.storage.database import SessionLocal


def main():

    model = EmbeddingModel()

    service = EmbeddingService(model)

    with SessionLocal() as session:
        chunk = session.scalar(select(Chunk).limit(1))

        if chunk is None:
            print("Chunks не найдены")
            return

        service.embed_chunk(chunk)

        session.commit()

        print(f"Chunk ID: {chunk.id}")

        print(f"Embedding bytes: {len(chunk.embedding)}")

        print(f"Embedding model: {chunk.embedding_model}")


if __name__ == "__main__":
    main()
