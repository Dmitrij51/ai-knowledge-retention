from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document


def get_document_by_hash(
    session: Session,
    file_hash: str,
) -> Document | None:
    """
    Возвращает документ по SHA-256 хешу.
    """

    stmt = select(Document).where(Document.file_hash == file_hash)

    return session.scalar(stmt)


def create_document(
    session: Session,
    file_path: str,
    file_hash: str,
) -> Document:
    """
    Создаёт документ в текущей SQLAlchemy-сессии.
    """

    path = Path(file_path)

    document = Document(
        filename=path.name,
        path=str(path.resolve()),
        file_type=path.suffix.lower().lstrip("."),
        file_hash=file_hash,
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


def update_document(
    session: Session,
    document: Document,
    file_hash: str,
) -> Document:
    """
    Обновляет информацию о существующем документе.
    """

    path = Path(document.path)

    document.filename = path.name
    document.file_type = path.suffix.lower().lstrip(".")
    document.file_hash = file_hash

    session.flush()

    return document


def get_documents(
    session: Session,
) -> list[Document]:
    """
    Возвращает все документы.
    """

    stmt = select(Document).order_by(Document.id)

    return list(session.scalars(stmt).all())


def get_document_by_path(
    session: Session,
    file_path: str,
) -> Document | None:
    """
    Возвращает документ по пути к файлу.
    """

    path = Path(file_path).resolve()

    stmt = select(Document).where(Document.path == str(path))

    return session.scalar(stmt)