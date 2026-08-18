from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.watched_folder import WatchedFolder


def add_watched_folder(
    session: Session,
    folder_path: str,
) -> WatchedFolder:
    """
    Добавляет папку в список отслеживаемых.
    """

    path = Path(folder_path).resolve()

    if not path.exists():
        raise FileNotFoundError(f"Папка не существует: {path}")

    if not path.is_dir():
        raise NotADirectoryError(f"Это не папка: {path}")

    existing = session.scalar(
        select(WatchedFolder).where(WatchedFolder.path == str(path))
    )

    if existing is not None:
        return existing

    folder = WatchedFolder(
        path=str(path),
        enabled=True,
    )

    session.add(folder)
    session.flush()

    return folder


def get_watched_folders(
    session: Session,
) -> list[WatchedFolder]:
    """
    Возвращает все включённые папки.
    """

    stmt = (
        select(WatchedFolder)
        .where(WatchedFolder.enabled.is_(True))
        .order_by(WatchedFolder.id)
    )

    return list(session.scalars(stmt).all())


def get_watched_folder(
    session: Session,
    folder_id: int,
) -> WatchedFolder | None:
    """
    Возвращает папку по ID.
    """

    return session.get(
        WatchedFolder,
        folder_id,
    )


def disable_watched_folder(
    session: Session,
    folder_id: int,
) -> bool:
    """
    Отключает отслеживание папки.
    """

    folder = session.get(
        WatchedFolder,
        folder_id,
    )

    if folder is None:
        return False

    folder.enabled = False

    session.flush()

    return True


def enable_watched_folder(
    session: Session,
    folder_id: int,
) -> bool:
    """
    Включает отслеживание папки.
    """

    folder = session.get(
        WatchedFolder,
        folder_id,
    )

    if folder is None:
        return False

    folder.enabled = True

    session.flush()

    return True


def delete_watched_folder(
    session: Session,
    folder_id: int,
) -> bool:
    """
    Полностью удаляет папку из списка отслеживания.
    """

    folder = session.get(
        WatchedFolder,
        folder_id,
    )

    if folder is None:
        return False

    session.delete(folder)
    session.flush()

    return True
