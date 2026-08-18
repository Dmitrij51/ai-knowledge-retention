from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document


def get_document_by_hash(
    session: Session,
    file_hash: str,
) -> Document | None:
    """
    Возвращает активный документ по SHA-256 хешу.
    Удалённые документы не учитываются.
    """

    stmt = select(Document).where(
        Document.file_hash == file_hash,
        Document.is_deleted.is_(False),
    )

    return session.scalar(stmt)


def create_document(
    session: Session,
    file_path: str,
    file_hash: str,
) -> Document:
    """
    Создаёт новый документ.
    """

    path = Path(file_path).resolve()

    document = Document(
        filename=path.name,
        path=str(path),
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
    document.is_deleted = False

    session.flush()

    return document


def get_documents(
    session: Session,
) -> list[Document]:
    """
    Возвращает только активные документы.
    """

    stmt = select(Document).where(Document.is_deleted.is_(False)).order_by(Document.id)

    return list(session.scalars(stmt).all())


def get_document_by_path(
    session: Session,
    file_path: str,
) -> Document | None:
    """
    Возвращает активный документ по пути.
    Удалённые документы не учитываются.
    """

    path = Path(file_path).resolve()

    stmt = select(Document).where(
        Document.path == str(path),
        Document.is_deleted.is_(False),
    )

    return session.scalar(stmt)


def mark_document_deleted(
    session: Session,
    document: Document,
) -> None:
    """
    Помечает документ как удалённый.

    Сам документ и его история версий
    остаются в базе данных.
    """

    document.is_deleted = True

    session.flush()

    print(
        f"[DELETE] Документ помечен как удалённый: "
        f"{document.filename} (ID={document.id})"
    )
