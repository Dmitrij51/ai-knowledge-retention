from pathlib import Path

from app.services.ingestion import ingest_document
from app.services.file_versioning import create_initial_version
from app.storage.database import SessionLocal
from app.storage.documents import get_document_by_path


SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".pdf",
    ".docx",
}


def scan_folder(folder_path: str) -> int:
    """
    Сканирует папку и все её подпапки.

    Для каждого поддерживаемого файла:
    - проверяет наличие документа в БД;
    - если документа нет — добавляет его;
    - создаёт первую версию.

    Возвращает количество найденных файлов.
    """

    root = Path(folder_path).resolve()

    if not root.exists():
        print(f"[SCAN] Папка не существует: {root}")
        return 0

    if not root.is_dir():
        print(f"[SCAN] Это не папка: {root}")
        return 0

    print(f"[SCAN] Сканирование: {root}")

    files = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    print(f"[SCAN] Найдено файлов: {len(files)}")

    added = 0

    for path in files:
        path = path.resolve()

        with SessionLocal() as session:
            document = get_document_by_path(
                session,
                str(path),
            )

        if document is not None:
            print(
                f"[SCAN] Уже зарегистрирован: {path}"
            )
            continue

        try:
            document_id = ingest_document(str(path))

            create_initial_version(str(path))

            print(
                f"[SCAN] Добавлен: {path} "
                f"(Document ID={document_id})"
            )

            added += 1

        except Exception as exc:
            print(
                f"[SCAN ERROR] Не удалось обработать: "
                f"{path} | {exc}"
            )

    print(
        f"[SCAN] Завершено. "
        f"Добавлено новых файлов: {added}"
    )

    return len(files)
