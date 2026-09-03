import time
from pathlib import Path
from threading import Lock, Timer

from watchdog.events import FileSystemEventHandler

from app.services.file_versioning import process_file_change
from app.services.ingestion import ingest_document
from app.storage.database import SessionLocal
from app.storage.documents import (
    get_document_by_path,
    mark_document_deleted,
)

SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".pdf",
    ".docx",
}


DEBOUNCE_SECONDS = 1.5


class FileWatcherHandler(FileSystemEventHandler):
    """
    Следит за файлами внутри одной папки.

    Поддерживает:

    - создание;
    - изменение;
    - удаление;
    - переименование;
    - перемещение.
    """

    def __init__(self):
        super().__init__()

        self._timers: dict[str, Timer] = {}

        self._lock = Lock()

    # ================================================================
    # HELPERS
    # ================================================================

    def _is_supported_file(
        self,
        path: str,
    ) -> bool:
        """
        Проверяет расширение файла.
        """

        return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS

    def _cancel_timer(
        self,
        path: str,
    ) -> None:
        """
        Отменяет отложенную обработку.
        """

        path = str(Path(path).resolve())

        with self._lock:
            timer = self._timers.pop(
                path,
                None,
            )

        if timer is not None:
            timer.cancel()

    def _schedule_file_processing(
        self,
        path: str,
        callback,
    ) -> None:
        """
        Выполняет debounce.

        Несколько быстрых MODIFY превращаются
        в одну обработку.
        """

        path = str(Path(path).resolve())

        self._cancel_timer(path)

        timer = Timer(
            DEBOUNCE_SECONDS,
            self._run_scheduled,
            args=(path, callback),
        )

        timer.daemon = True

        with self._lock:
            self._timers[path] = timer

        timer.start()

    def _run_scheduled(
        self,
        path: str,
        callback,
    ) -> None:

        with self._lock:
            self._timers.pop(
                path,
                None,
            )

        try:
            callback(path)

        except Exception as exc:
            print(f"[WATCHER ERROR] Ошибка обработки {path}: {exc}")

    def _wait_until_file_is_stable(
        self,
        path: str,
        attempts: int = 10,
        delay: float = 0.3,
    ) -> bool:
        """
        Ждёт стабилизации размера файла.
        """

        file_path = Path(path)

        previous_size = None

        for _ in range(attempts):
            if not file_path.exists():
                return False

            try:
                current_size = file_path.stat().st_size

            except OSError:
                time.sleep(delay)
                continue

            if previous_size is not None and current_size == previous_size:
                return True

            previous_size = current_size

            time.sleep(delay)

        return file_path.exists()

    # ================================================================
    # CREATE
    # ================================================================

    def on_created(self, event):
        """
        Новый файл.
        """

        if event.is_directory:
            return

        path = event.src_path

        if not self._is_supported_file(path):
            return

        print(f"[WATCHER] Новый файл: {path}")

        self._schedule_file_processing(
            path,
            self._process_created_file,
        )

    def _process_created_file(
        self,
        path: str,
    ) -> None:
        """
        Индексирует новый файл.
        """

        file_path = Path(path)

        if not file_path.exists():
            return

        if not file_path.is_file():
            return

        if not self._wait_until_file_is_stable(path):
            print(f"[WATCHER] Файл не стабилизировался: {path}")

            return

        print(f"[WATCHER] Индексация нового файла: {path}")

        ingest_document(path)

        # initial version создаётся
        # отдельным pipeline.
        from app.services.file_versioning import (
            create_initial_version,
        )

        create_initial_version(path)

        print(f"[WATCHER] Новый файл проиндексирован: {path}")

    # ================================================================
    # MODIFY
    # ================================================================

    def on_modified(self, event):
        """
        Изменение файла.
        """

        if event.is_directory:
            return

        path = event.src_path

        if not self._is_supported_file(path):
            return

        print(f"[WATCHER] Изменение файла: {path}")

        self._schedule_file_processing(
            path,
            self._process_modified_file,
        )

    def _process_modified_file(
        self,
        path: str,
    ) -> None:
        """
        Обрабатывает изменение файла.

        process_file_change()
        сам проверяет hash.
        """

        file_path = Path(path)

        if not file_path.exists():
            return

        if not file_path.is_file():
            return

        if not self._wait_until_file_is_stable(path):
            print(f"[WATCHER] Файл не стабилизировался: {path}")

            return

        print(f"[WATCHER] Переиндексация: {path}")

        process_file_change(path)

        print(f"[WATCHER] Переиндексация завершена: {path}")

    # ================================================================
    # DELETE
    # ================================================================

    def on_deleted(self, event):
        """
        Файл удалён.
        """

        if event.is_directory:
            return

        path = event.src_path

        if not self._is_supported_file(path):
            return

        self._cancel_timer(path)

        print(f"[WATCHER] Файл удалён: {path}")

        try:
            with SessionLocal() as session:
                document = get_document_by_path(
                    session,
                    path,
                )

                if document is None:
                    print(f"[WATCHER] Документ не найден в БД: {path}")

                    return

                mark_document_deleted(
                    session,
                    document,
                )

                session.commit()

            print(f"[WATCHER] Документ помечен удалённым: {path}")

        except Exception as exc:
            print(f"[WATCHER ERROR] Ошибка удаления {path}: {exc}")

    # ================================================================
    # MOVE / RENAME
    # ================================================================

    def on_moved(self, event):
        """
        Файл был перемещён или переименован.
        """

        if event.is_directory:
            return

        old_path = event.src_path
        new_path = event.dest_path

        old_supported = self._is_supported_file(old_path)

        new_supported = self._is_supported_file(new_path)

        if not old_supported and not new_supported:
            return

        print(f"[WATCHER] Файл перемещён:\n    FROM: {old_path}\n    TO:   {new_path}")

        self._cancel_timer(old_path)
        self._cancel_timer(new_path)

        # ------------------------------------------------------------
        # supported → unsupported
        #
        # file.md → file.exe
        # ------------------------------------------------------------

        if old_supported and not new_supported:
            self._mark_deleted(old_path)

            return

        # ------------------------------------------------------------
        # unsupported → supported
        #
        # file.exe → file.md
        # ------------------------------------------------------------

        if not old_supported and new_supported:
            self._schedule_file_processing(
                new_path,
                self._process_created_file,
            )

            return

        # ------------------------------------------------------------
        # supported → supported
        #
        # old.md → new.md
        #
        # Старый путь закрываем,
        # новый индексируем.
        # ------------------------------------------------------------

        self._mark_deleted(old_path)

        self._schedule_file_processing(
            new_path,
            self._process_created_file,
        )

    # ================================================================
    # DELETE HELPER
    # ================================================================

    def _mark_deleted(
        self,
        path: str,
    ) -> None:
        """
        Помечает Document как удалённый.
        """

        try:
            with SessionLocal() as session:
                document = get_document_by_path(
                    session,
                    path,
                )

                if document is None:
                    return

                mark_document_deleted(
                    session,
                    document,
                )

                session.commit()

            print(f"[WATCHER] Документ помечен удалённым: {path}")

        except Exception as exc:
            print(f"[WATCHER ERROR] Ошибка soft-delete {path}: {exc}")
