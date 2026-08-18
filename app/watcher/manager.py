from watchdog.observers import Observer

from app.storage.database import SessionLocal
from app.storage.watched_folders import get_watched_folders
from app.watcher.watcher import FileWatcherHandler


class WatcherManager:
    """
    Управляет наблюдением за всеми папками,
    которые пользователь выбрал для отслеживания.
    """

    def __init__(self):
        self.observer = Observer()

    def start(self) -> int:
        """
        Загружает включённые папки из БД
        и запускает Watchdog для каждой.

        Возвращает количество отслеживаемых папок.
        """

        with SessionLocal() as session:
            folders = get_watched_folders(session)

            if not folders:
                print("Нет папок для отслеживания.")
                return 0

            for folder in folders:
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
        """
        Останавливает Watchdog.
        """

        if not self.observer.is_alive():
            return

        print("Остановка наблюдения...")

        self.observer.stop()
        self.observer.join()

        print("Наблюдение остановлено.")

