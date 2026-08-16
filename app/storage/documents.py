from pathlib import Path
from sqlalchemy import select
from app.models.document import Document
from app.storage.database import SessionLocal


def create_document(file_path: str) -> Document:
    """
    Добавляет документ в базу данных.
    """

    path = Path(file_path)

    document = Document(
        filename=path.name,
        path=str(path.resolve()),
        file_type=path.suffix.lower().lstrip("."),
    )

    with SessionLocal() as session:
        session.add(document)
        session.commit()
        session.refresh(document)

        return document


def get_document(document_id: int) -> Document | None:
    """
    Возвращает документ по ID.
    """

    with SessionLocal() as session:
        return session.get(Document, document_id)


def get_documents() -> list[Document]:
    """
    Возвращает все документы.
    """

    with SessionLocal() as session:
        result = session.execute(select(Document).order_by(Document.id))

        return list(result.scalars().all())