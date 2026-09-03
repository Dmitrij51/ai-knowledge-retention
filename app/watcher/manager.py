from pathlib import Path
from threading import RLock

from watchdog.observers import Observer

from app.storage.database import SessionLocal
from app.storage.watched_folders import (
    add_watched_folder,
    delete_watched_folder,
    disable_watched_folder,
    enable_watched_folder,
    get_watched_folder,
    get_watched_folders,
)
from app.watcher.scanner import scan_folder
from app.watcher.watcher import FileWatcherHandler


class WatcherManager:
    """
    Управляет всеми папками, за которыми следит приложение.

    Поддерживает:

    - запуск watchdog;
    - остановку watchdog;
    - добавление папки без перезапуска приложения;
    - удаление папки из наблюдения;
    - включение/отключение наблюдения;
    - первоначальное сканирование;
    - повторное сканирование.
    """

    def __init__(self):
        self.observer = Observer()

        self.lock = RLock()

        self.started = False

        self.watches: dict[str, object] = {}

        self.handlers: dict[str, FileWatcherHandler] = {}

    # ================================================================
    # START
    # ================================================================

    def start(self) -> int:
        """
        Запускает watchdog и подключает все активные папки из БД.

        Возвращает количество реально подключённых папок.
        """

        with self.lock:
            if self.started:
                return len(self.watches)

            print("[WATCHER] Запуск...")

            self.observer.start()

            self.started = True

            with SessionLocal() as session:
                folders = get_watched_folders(session)

            started_count = 0

            for folder in folders:
                try:
                    path = self._normalize_path(folder.path)

                    self._schedule(path)

                    # Initial scan.
                    scan_folder(path)

                    started_count += 1

                except (
                    FileNotFoundError,
                    NotADirectoryError,
                ) as exc:
                    print(f"[WATCHER] Папка недоступна: {folder.path} | {exc}")

                except Exception as exc:
                    print(f"[WATCHER ERROR] Не удалось подключить {folder.path}: {exc}")

            print(f"[WATCHER] Запущен. Активных папок: {started_count}")

            return started_count

    # ================================================================
    # STOP
    # ================================================================

    def stop(self) -> None:
        """
        Полностью останавливает watchdog.
        """

        with self.lock:
            if not self.started:
                return

            print("[WATCHER] Остановка...")

            try:
                self.observer.stop()
                self.observer.join(timeout=5)

            except Exception as exc:
                print(f"[WATCHER ERROR] Ошибка остановки: {exc}")

            self.watches.clear()
            self.handlers.clear()

            self.started = False

            print("[WATCHER] Остановлен.")

    # ================================================================
    # PATH
    # ================================================================

    def _normalize_path(
        self,
        folder_path: str,
    ) -> str:
        """
        Нормализует путь и проверяет существование папки.
        """

        if not folder_path or not folder_path.strip():
            raise ValueError("Путь к папке не указан.")

        path = Path(folder_path).expanduser().resolve()

        if not path.exists():
            raise FileNotFoundError(f"Папка не существует: {path}")

        if not path.is_dir():
            raise NotADirectoryError(f"Указанный путь не является папкой: {path}")

        return str(path)

    # ================================================================
    # SCHEDULE
    # ================================================================

    def _schedule(
        self,
        folder_path: str,
    ) -> None:
        """
        Начинает наблюдение за папкой.
        """

        path = self._normalize_path(folder_path)

        if not self.started:
            raise RuntimeError("WatcherManager ещё не запущен.")

        if path in self.watches:
            return

        handler = FileWatcherHandler()

        watch = self.observer.schedule(
            handler,
            path,
            recursive=True,
        )

        self.handlers[path] = handler
        self.watches[path] = watch

        print(f"[WATCHER] Наблюдение добавлено: {path}")

    def _unschedule(
        self,
        folder_path: str,
    ) -> None:
        """
        Прекращает наблюдение за папкой.
        """

        path = str(Path(folder_path).expanduser().resolve())

        watch = self.watches.pop(
            path,
            None,
        )

        self.handlers.pop(
            path,
            None,
        )

        if watch is None:
            return

        try:
            self.observer.unschedule(watch)

            print(f"[WATCHER] Наблюдение удалено: {path}")

        except Exception as exc:
            print(f"[WATCHER ERROR] Не удалось остановить наблюдение {path}: {exc}")

    # ================================================================
    # ADD FOLDER
    # ================================================================

    def add_folder(
        self,
        folder_path: str,
    ) -> int:
        """
        Добавляет папку в БД.

        Если watcher уже работает,
        папка подключается сразу.

        После добавления выполняется initial scan.
        """

        path = self._normalize_path(folder_path)

        with self.lock:
            with SessionLocal() as session:
                folder = add_watched_folder(
                    session,
                    path,
                )

                session.commit()

                folder_id = folder.id

            if self.started:
                try:
                    self._schedule(path)

                    scan_folder(path)

                except Exception:
                    self._unschedule(path)

                    raise

            print(f"[WATCHER] Папка добавлена: {path}")

            return folder_id

    # ================================================================
    # RESCAN
    # ================================================================

    def rescan_folder(
        self,
        folder_id: int,
    ) -> int:
        """
        Повторно сканирует папку.
        """

        with self.lock:
            with SessionLocal() as session:
                folder = get_watched_folder(
                    session,
                    folder_id,
                )

                if folder is None:
                    raise ValueError(f"Папка с ID={folder_id} не найдена.")

                path = folder.path

            return scan_folder(path)

    # ================================================================
    # ENABLE
    # ================================================================

    def enable_folder(
        self,
        folder_id: int,
    ) -> None:
        """
        Включает наблюдение за папкой.
        """

        with self.lock:
            with SessionLocal() as session:
                folder = get_watched_folder(
                    session,
                    folder_id,
                )

                if folder is None:
                    raise ValueError(f"Папка с ID={folder_id} не найдена.")

                path = folder.path

                enable_watched_folder(
                    session,
                    folder_id,
                )

                session.commit()

            if self.started:
                self._normalize_path(path)

                self._schedule(path)

                scan_folder(path)

            print(f"[WATCHER] Папка включена: {path}")

    # ================================================================
    # DISABLE
    # ================================================================

    def disable_folder(
        self,
        folder_id: int,
    ) -> None:
        """
        Отключает наблюдение.

        Документы из БД не удаляются.
        """

        with self.lock:
            with SessionLocal() as session:
                folder = get_watched_folder(
                    session,
                    folder_id,
                )

                if folder is None:
                    raise ValueError(f"Папка с ID={folder_id} не найдена.")

                path = folder.path

                disable_watched_folder(
                    session,
                    folder_id,
                )

                session.commit()

            if self.started:
                self._unschedule(path)

            print(f"[WATCHER] Наблюдение отключено: {path}")

    # ================================================================
    # DELETE
    # ================================================================

    def delete_folder(
        self,
        folder_id: int,
    ) -> None:
        """
        Удаляет папку только из списка наблюдения.

        Физическая папка НЕ удаляется.

        Документы также НЕ удаляются.
        """

        with self.lock:
            with SessionLocal() as session:
                folder = get_watched_folder(
                    session,
                    folder_id,
                )

                if folder is None:
                    raise ValueError(f"Папка с ID={folder_id} не найдена.")

                path = folder.path

                delete_watched_folder(
                    session,
                    folder_id,
                )

                session.commit()

            if self.started:
                self._unschedule(path)

            print(f"[WATCHER] Папка удалена из наблюдения: {path}")
