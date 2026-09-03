from pathlib import Path

from app.services.file_versioning import (
    create_initial_version,
    process_file_change,
)
from app.services.ingestion import ingest_document
from app.storage.database import SessionLocal
from app.storage.documents import (
    get_document_by_path,
)
from app.storage.file_hash import calculate_file_hash


SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".pdf",
    ".docx",
}


def is_supported_file(path: Path) -> bool:
    """
    Проверяет, поддерживается ли файл.
    """

    return path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS


def scan_folder(
    folder_path: str,
) -> int:
    """
    Сканирует папку и все подпапки.

    Для каждого поддерживаемого файла:

        новый файл
            ↓
        ingest_document()
            ↓
        initial version

        существующий без изменений
            ↓
        пропускаем

        существующий изменённый
            ↓
        process_file_change()
            ↓
        re-ingest + FileVersion + Diff
    """

    root = Path(folder_path).expanduser().resolve()

    if not root.exists():
        raise FileNotFoundError(f"Папка не существует: {root}")

    if not root.is_dir():
        raise NotADirectoryError(f"Это не папка: {root}")

    files = sorted(
        (path.resolve() for path in root.rglob("*") if is_supported_file(path)),
        key=lambda path: str(path).lower(),
    )

    print(f"[SCAN] {root}: найдено {len(files)} поддерживаемых файлов")

    processed = 0

    for path in files:
        try:
            file_path = str(path)

            file_hash = calculate_file_hash(file_path)

            with SessionLocal() as session:
                document = get_document_by_path(
                    session,
                    file_path,
                )

            # --------------------------------------------------------
            # Новый файл
            # --------------------------------------------------------

            if document is None:
                print(f"[SCAN] Новый файл: {path}")

                ingest_document(file_path)

                create_initial_version(file_path)

                processed += 1

                print(f"[SCAN] Добавлен: {path}")

                continue

            # --------------------------------------------------------
            # Файл существует и не изменился
            # --------------------------------------------------------

            if document.file_hash == file_hash:
                print(f"[SCAN] Без изменений: {path}")

                continue

            # --------------------------------------------------------
            # Файл изменился
            # --------------------------------------------------------

            print(f"[SCAN] Изменён: {path}")

            process_file_change(file_path)

            processed += 1

            print(f"[SCAN] Обновлён: {path}")

        except PermissionError as exc:
            print(f"[SCAN ERROR] Нет доступа: {path} | {exc}")

        except OSError as exc:
            print(f"[SCAN ERROR] Ошибка файловой системы: {path} | {exc}")

        except Exception as exc:
            print(f"[SCAN ERROR] {path} | {exc}")

    print(f"[SCAN] Завершено: {root} | обработано/обновлено: {processed}")

    return processed
