from watchdog.observers import Observer

from app.storage.database import SessionLocal
from app.storage.watched_folders import get_watched_folders
from app.watcher.scanner import scan_folder
from app.watcher.watcher import FileWatcherHandler


class WatcherManager:

    def __init__(self):
        self.observer = Observer()

    def start(self) -> int:

        with SessionLocal() as session:
            folders = get_watched_folders(session)

            if not folders:
                print("Нет папок для отслеживания.")
                return 0

            for folder in folders:

                # Сначала обрабатываем уже существующие файлы
                scan_folder(folder.path)

                # Затем запускаем наблюдение
                print(
                    f"Запускаем наблюдение: {folder.path}"
                )

                handler = FileWatcherHandler()

                self.observer.schedule(
                    handler,
                    folder.path,
                    recursive=True,
                )

        self.observer.start()

        print(
            f"Наблюдение запущено для "
            f"{len(folders)} папок."
        )

        return len(folders)

    def stop(self) -> None:

        if not self.observer.is_alive():
            return

        print("Остановка наблюдения...")

        self.observer.stop()
        self.observer.join()

        print("Наблюдение остановлено.")
