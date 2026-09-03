from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.chunk import Chunk


def create_chunks(
    session: Session,
    document_id: int,
    chunks: list[str],
) -> list[Chunk]:
    """
    Создаёт chunks документа в текущей SQLAlchemy-сессии.

    Каждый chunk получает последовательный chunk_index:

        0
        1
        2
        ...

    Embeddings создаются отдельно в ingestion.py.
    """

    if not chunks:
        return []

    chunk_objects: list[Chunk] = []

    for index, content in enumerate(chunks):
        if content is None:
            continue

        content = str(content).strip()

        if not content:
            continue

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
) -> int:
    """
    Удаляет все chunks конкретного документа.

    Возвращает количество удалённых chunks.

    Используется при переиндексации:

        старый файл
            ↓
        удалить старые chunks
            ↓
        создать новые chunks
    """

    stmt = delete(Chunk).where(Chunk.document_id == document_id)

    result = session.execute(stmt)

    deleted_count = result.rowcount or 0

    return deleted_count


def get_chunks(
    session: Session,
    document_id: int,
) -> list[Chunk]:
    """
    Возвращает все chunks конкретного документа.

    Используется для:

    - просмотра документа;
    - диагностики;
    - RAG;
    - проверки переиндексации.
    """

    stmt = (
        select(Chunk)
        .where(Chunk.document_id == document_id)
        .order_by(Chunk.chunk_index)
    )

    return list(session.scalars(stmt).all())


def get_chunk(
    session: Session,
    chunk_id: int,
) -> Chunk | None:
    """
    Возвращает один chunk по ID.
    """

    return session.get(
        Chunk,
        chunk_id,
    )


def get_all_chunks(
    session: Session,
) -> list[Chunk]:
    """
    Возвращает все chunks.

    Используется преимущественно
    для диагностики и тестирования.
    """

    stmt = select(Chunk).order_by(
        Chunk.document_id,
        Chunk.chunk_index,
    )

    return list(session.scalars(stmt).all())
