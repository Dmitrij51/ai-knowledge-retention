from pathlib import Path

from app.processing.diff import create_diff
from app.parsers.document_loader import load_document
from app.storage.database import SessionLocal
from app.storage.documents import get_document_by_path
from app.storage.file_hash import calculate_file_hash
from app.storage.file_versions import (
    create_file_version,
    get_latest_version,
)

def create_initial_version(file_path: str) -> None:
    """
    Создаёт первую версию уже зарегистрированного документа.

    Используется при первоначальном добавлении нового файла.
    """

    path = Path(file_path).resolve()

    if not path.exists() or not path.is_file():
        print(f"[SKIP] Файл не существует: {path}")
        return

    try:
        file_hash = calculate_file_hash(str(path))
    except (OSError, PermissionError) as error:
        print(
            f"[ERROR] Не удалось вычислить hash: "
            f"{path} | {error}"
        )
        return

    try:
        content = load_document(str(path))
    except Exception as error:
        print(
            f"[ERROR] Не удалось прочитать файл: "
            f"{path} | {error}"
        )
        return

    if not content.strip():
        print(f"[SKIP] Файл пустой: {path}")
        return

    with SessionLocal() as session:

        document = get_document_by_path(
            session,
            str(path),
        )

        if document is None:
            print(
                f"[ERROR] Документ не найден в БД: {path}"
            )
            return

        latest_version = get_latest_version(
            session,
            document.id,
        )

        if latest_version is not None:
            print(
                f"[SKIP] Первая версия уже существует: "
                f"{path}"
            )
            return

        version = create_file_version(
            session=session,
            document_id=document.id,
            file_hash=file_hash,
            content=content,
        )

        session.commit()

        print(
            f"[VERSION] Создана первая версия: "
            f"{path} | Version={version.version}"
        )




def process_file_change(file_path: str) -> None:
    """
    Обрабатывает изменение файла.

    Алгоритм:

    файл изменился
        ↓
    найти Document
        ↓
    вычислить hash
        ↓
    проверить последнюю версию
        ↓
    прочитать файл
        ↓
    создать новую версию
        ↓
    создать Diff
    """

    path = Path(file_path).resolve()

    if not path.exists():
        print(f"[SKIP] Файл больше не существует: {path}")
        return

    if not path.is_file():
        return

    try:
        file_hash = calculate_file_hash(str(path))

    except (OSError, PermissionError) as error:
        print(f"[ERROR] Не удалось вычислить hash: {path} | {error}")
        return

    with SessionLocal() as session:

        # ---------------------------------
        # 1. Находим Document
        # ---------------------------------

        document = get_document_by_path(
            session,
            str(path),
        )

        if document is None:
            print(
                f"[SKIP] Файл ещё не зарегистрирован: {path}"
            )
            return

        # ---------------------------------
        # 2. Получаем последнюю версию
        # ---------------------------------

        latest_version = get_latest_version(
            session,
            document.id,
        )

        # ---------------------------------
        # 3. Проверяем hash
        # ---------------------------------

        if (
            latest_version is not None
            and latest_version.file_hash == file_hash
        ):
            print(
                f"[SKIP] Файл не изменился: {path}"
            )
            return

        # ---------------------------------
        # 4. Читаем файл
        # ---------------------------------

        try:
            content = load_document(str(path))

        except Exception as error:
            print(
                f"[ERROR] Не удалось прочитать файл: "
                f"{path} | {error}"
            )
            return

        if not content.strip():
            print(
                f"[SKIP] Файл пустой: {path}"
            )
            return

        # ---------------------------------
        # 5. Создаём новую версию
        # ---------------------------------

        new_version = create_file_version(
            session=session,
            document_id=document.id,
            file_hash=file_hash,
            content=content,
        )

        # ---------------------------------
        # 6. Создаём Diff
        # ---------------------------------

        if latest_version is not None:

            diff = create_diff(
                latest_version.content,
                new_version.content,
            )

            print(
                f"\n[VERSION] {path}"
            )

            print(
                f"Version: "
                f"{new_version.version}"
            )

            print(
                f"Diff:\n{diff}"
            )

        else:

            print(
                f"[VERSION] Создана первая версия: "
                f"{path}"
            )

        # ---------------------------------
        # 7. Сохраняем
        # ---------------------------------

        session.commit()
