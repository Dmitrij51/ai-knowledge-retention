from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.models.chunk import Chunk


def create_chunks(
    session: Session,
    document_id: int,
    chunks: list[str],
) -> list[Chunk]:
    """
    Создаёт chunks документа в текущей SQLAlchemy-сессии.
    """

    chunk_objects = []

    for index, content in enumerate(chunks):
        chunk = Chunk(
            document_id=document_id,
            chunk_index=index,
            content=content,
        )

        session.add(chunk)
        chunk_objects.append(chunk)

    session.flush()

    return chunk_objects


def delete_document_chunks(
    session: Session,
    document_id: int,
) -> None:
    """
    Удаляет все chunks документа.
    """

    stmt = delete(Chunk).where(Chunk.document_id == document_id)

    session.execute(stmt)


def get_chunks(
    session: Session,
    document_id: int,
) -> list[Chunk]:
    """
    Возвращает все chunks конкретного документа.
    """

    stmt = (
        select(Chunk)
        .where(Chunk.document_id == document_id)
        .order_by(Chunk.chunk_index)
    )

    return list(session.scalars(stmt).all())
