from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document


# ================================================================
# PATH NORMALIZATION
# ================================================================


def _normalize_path(file_path: str) -> str:
    """
    Приводит путь к единому абсолютному виду.

    Например:

        C:\\Project\\test.txt

    и:

        C:/Project/test.txt

    должны восприниматься как один и тот же файл.
    """

    if not file_path or not file_path.strip():
        raise ValueError("Путь к файлу не указан.")

    return str(Path(file_path).expanduser().resolve())


# ================================================================
# GET BY HASH
# ================================================================


def get_document_by_hash(
    session: Session,
    file_hash: str,
) -> Document | None:
    """
    Возвращает активный документ по SHA-256 hash.

    Soft-deleted документы не учитываются.
    """

    if not file_hash:
        return None

    stmt = select(Document).where(
        Document.file_hash == file_hash,
        Document.is_deleted.is_(False),
    )

    return session.scalar(stmt)


# ================================================================
# GET BY PATH
# ================================================================


def get_document_by_path(
    session: Session,
    file_path: str,
) -> Document | None:
    """
    Возвращает активный документ по абсолютному пути.

    Soft-deleted документы не учитываются.
    """

    normalized_path = _normalize_path(file_path)

    stmt = select(Document).where(
        Document.path == normalized_path,
        Document.is_deleted.is_(False),
    )

    return session.scalar(stmt)


def get_document_by_path_any(
    session: Session,
    file_path: str,
) -> Document | None:
    """
    Возвращает документ по пути независимо
    от значения is_deleted.

    Используется для восстановления
    ранее удалённого документа.
    """

    normalized_path = _normalize_path(file_path)

    stmt = select(Document).where(
        Document.path == normalized_path,
    )

    return session.scalar(stmt)


# ================================================================
# GET BY ID
# ================================================================


def get_document(
    session: Session,
    document_id: int,
) -> Document | None:
    """
    Возвращает документ по ID.

    Может вернуть как активный,
    так и soft-deleted документ.
    """

    return session.get(
        Document,
        document_id,
    )


# ================================================================
# CREATE
# ================================================================


def create_document(
    session: Session,
    file_path: str,
    file_hash: str,
) -> Document:
    """
    Создаёт новый Document.
    """

    if not file_hash:
        raise ValueError("file_hash не может быть пустым.")

    normalized_path = _normalize_path(file_path)

    path = Path(normalized_path)

    document = Document(
        filename=path.name,
        path=normalized_path,
        file_type=path.suffix.lower().lstrip("."),
        file_hash=file_hash,
        is_deleted=False,
    )

    session.add(document)
    session.flush()

    return document


# ================================================================
# UPDATE
# ================================================================


def update_document(
    session: Session,
    document: Document,
    file_hash: str,
    file_path: str | None = None,
) -> Document:
    """
    Обновляет существующий Document.

    Обновляет:

    - hash;
    - path;
    - filename;
    - file_type;
    - is_deleted.

    Если file_path не передан,
    используется существующий document.path.

    is_deleted устанавливается в False,
    поэтому функция также используется
    для восстановления документа.
    """

    if not file_hash:
        raise ValueError("file_hash не может быть пустым.")

    if file_path is not None:
        document.path = _normalize_path(file_path)

    path = Path(document.path)

    document.filename = path.name

    document.file_type = path.suffix.lower().lstrip(".")

    document.file_hash = file_hash

    # Важно:
    #
    # если документ был soft-deleted,
    # update означает его восстановление.
    document.is_deleted = False

    session.flush()

    return document


# ================================================================
# RESTORE
# ================================================================


def restore_document(
    session: Session,
    document: Document,
    file_hash: str,
) -> Document:
    """
    Восстанавливает soft-deleted документ.

    Создавать новый Document не нужно.
    Существующая запись и её история сохраняются.
    """

    if not document.is_deleted:
        return document

    return update_document(
        session=session,
        document=document,
        file_hash=file_hash,
    )


# ================================================================
# LIST
# ================================================================


def get_documents(
    session: Session,
) -> list[Document]:
    """
    Возвращает только активные документы.
    """

    stmt = select(Document).where(Document.is_deleted.is_(False)).order_by(Document.id)

    return list(session.scalars(stmt).all())


def get_all_documents(
    session: Session,
) -> list[Document]:
    """
    Возвращает все документы,
    включая soft-deleted.
    """

    stmt = select(Document).order_by(Document.id)

    return list(session.scalars(stmt).all())


# ================================================================
# SOFT DELETE
# ================================================================


def mark_document_deleted(
    session: Session,
    document: Document,
) -> None:
    """
    Помечает документ как удалённый.

    Физически запись из БД не удаляется.

    Сохраняются:

    - Document;
    - FileVersion;
    - Diff;
    - история;
    - возможность восстановления.
    """

    if document.is_deleted:
        return

    document.is_deleted = True

    session.flush()

    print(
        "[DELETE] "
        f"Документ помечен как удалённый: "
        f"{document.filename} "
        f"(ID={document.id})"
    )


# ================================================================
# SOFT DELETE BY PATH
# ================================================================


def mark_document_deleted_by_path(
    session: Session,
    file_path: str,
) -> bool:
    """
    Помечает активный документ по пути
    как удалённый.

    Возвращает:

        True  — документ найден;
        False — документ не найден.
    """

    document = get_document_by_path(
        session,
        file_path,
    )

    if document is None:
        return False

    mark_document_deleted(
        session,
        document,
    )

    return True
