from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.file_version import FileVersion


def get_versions(
    session: Session,
    document_id: int,
) -> list[FileVersion]:
    """
    Возвращает все версии документа
    от самой старой к самой новой.
    """

    stmt = (
        select(FileVersion)
        .where(FileVersion.document_id == document_id)
        .order_by(FileVersion.version)
    )

    return list(session.scalars(stmt).all())


def get_latest_version(
    session: Session,
    document_id: int,
) -> FileVersion | None:
    """
    Возвращает последнюю версию документа.
    """

    stmt = (
        select(FileVersion)
        .where(FileVersion.document_id == document_id)
        .order_by(FileVersion.version.desc())
        .limit(1)
    )

    return session.scalar(stmt)


def get_next_version_number(
    session: Session,
    document_id: int,
) -> int:
    """
    Возвращает номер следующей версии документа.

    Если версий ещё нет — возвращает 1.
    """

    latest_version = get_latest_version(
        session,
        document_id,
    )

    if latest_version is None:
        return 1

    return latest_version.version + 1


def create_file_version(
    session: Session,
    document_id: int,
    file_hash: str,
    content: str,
) -> FileVersion:
    """
    Создаёт новую версию файла.
    """

    version_number = get_next_version_number(
        session,
        document_id,
    )

    version = FileVersion(
        document_id=document_id,
        version=version_number,
        file_hash=file_hash,
        content=content,
    )

    session.add(version)
    session.flush()

    return version