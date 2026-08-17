from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document


def create_document(
    session: Session,
    file_path: str,
) -> Document:
    """
    Создаёт документ в текущей SQLAlchemy-сессии.
    """

    path = Path(file_path)

    document = Document(
        filename=path.name,
        path=str(path.resolve()),
        file_type=path.suffix.lower().lstrip("."),
    )

    session.add(document)
    session.flush()

    return document


def get_document(
    session: Session,
    document_id: int,
) -> Document | None:
    """
    Возвращает документ по ID.
    """

    return session.get(Document, document_id)


def get_documents(
    session: Session,
) -> list[Document]:
    """
    Возвращает все документы.
    """

    stmt = select(Document).order_by(Document.id)

    return list(session.scalars(stmt).all())
