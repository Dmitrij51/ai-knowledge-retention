from app.models.chunk import Chunk
from app.storage.database import SessionLocal


def create_chunks(
    document_id: int,
    chunks: list[str],
) -> list[Chunk]:
    """
    Сохраняет chunks документа в базе данных.
    """

    chunk_objects = []

    with SessionLocal() as session:
        for index, content in enumerate(chunks):
            chunk = Chunk(
                document_id=document_id,
                chunk_index=index,
                content=content,
            )

            session.add(chunk)
            chunk_objects.append(chunk)

        session.commit()

        for chunk in chunk_objects:
            session.refresh(chunk)

        return chunk_objects


def get_chunks(document_id: int) -> list[Chunk]:
    """
    Возвращает все chunks конкретного документа.
    """

    with SessionLocal() as session:
        chunks = (
            session.query(Chunk)
            .filter(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
            .all()
        )

        return chunks
