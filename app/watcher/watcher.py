from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from app.services.file_versioning import (
    process_file_change,
    create_initial_version,
)
from app.services.ingestion import ingest_document
from app.storage.database import SessionLocal
from app.storage.documents import (
    get_document_by_path,
    mark_document_deleted,
)
from app.watcher.debounce import Debouncer


SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".pdf",
    ".docx",
}


class FileWatcherHandler(FileSystemEventHandler):
    """
    Обрабатывает события файловой системы.
    """

    def __init__(self):
        super().__init__()

        # Ждём 1 секунду после последнего
        # изменения файла.
        self.debouncer = Debouncer(delay=1.0)

    def on_created(self, event):
        if event.is_directory:
            return

        path = Path(event.src_path)

        print(f"[CREATED] {path}")

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            print(f"[SKIP] Неподдерживаемый формат: {path}")
            return

        try:
            if not path.exists():
                print(f"[SKIP] Файл уже не существует: {path}")
                return

            document_id = ingest_document(str(path))

            print(f"[INGEST] Новый файл добавлен: {path} (Document ID={document_id})")

            # Создаём первую версию.
            create_initial_version(str(path))

        except Exception as exc:
            print(f"[ERROR] Не удалось добавить файл: {path} | {exc}")

    def on_modified(self, event):
        if event.is_directory:
            return

        path = Path(event.src_path)

        print(f"[MODIFIED] {path}")

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            print(f"[SKIP] Неподдерживаемый формат: {path}")
            return

        # Не обрабатываем изменение сразу.
        # Debouncer дождётся окончания серии изменений.
        self.debouncer.call(
            str(path),
            self._process_modified,
        )

    def _process_modified(
        self,
        file_path: str,
    ):
        """
        Обрабатывает изменение файла
        после debounce.
        """

        try:
            print(f"[DEBOUNCE] Обрабатываем: {file_path}")

            process_file_change(file_path)

        except Exception as exc:
            print(f"[ERROR] Не удалось обработать изменение: {file_path} | {exc}")

    def on_deleted(self, event):
        if event.is_directory:
            return

        path = Path(event.src_path)

        print(f"[DELETED] {path}")

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return

        try:
            with SessionLocal() as session:
                document = get_document_by_path(
                    session,
                    str(path.resolve()),
                )

                if document is None:
                    print(f"[DELETE] Документ не найден в БД: {path}")
                    return

                mark_document_deleted(
                    session,
                    document,
                )

                session.commit()

        except Exception as exc:
            print(f"[ERROR] Не удалось обработать удаление: {path} | {exc}")

    def on_moved(self, event):
        if event.is_directory:
            return

        print(f"[MOVED] {event.src_path} -> {event.dest_path}")


def start_watcher(path: str):
    """
    Запускает наблюдение за папкой
    и всеми её подпапками.
    """

    watch_path = Path(path).resolve()

    if not watch_path.exists():
        raise FileNotFoundError(f"Папка не существует: {watch_path}")

    if not watch_path.is_dir():
        raise NotADirectoryError(f"Это не папка: {watch_path}")

    event_handler = FileWatcherHandler()

    observer = Observer()

    observer.schedule(
        event_handler,
        str(watch_path),
        recursive=True,
    )

    observer.start()

    print(f"Наблюдение запущено: {watch_path}")

    print("Изменяй, создавай или удаляй файлы...")

    print("Для остановки нажми Ctrl+C")

    try:
        while True:
            pass

    except KeyboardInterrupt:
        print("\nОстановка наблюдения...")

        observer.stop()

    observer.join()


if __name__ == "__main__":
    start_watcher("test")
