from watchdog.observers import Observer

from app.storage.database import SessionLocal
from app.storage.watched_folders import get_watched_folders
from app.watcher.watcher import FileWatcherHandler


class WatcherManager:
    """
    Управляет наблюдением за всеми папками,
    которые пользователь выбрал для запоминания.
    """

    def __init__(self):
        self.observer = Observer()

    def start(self):
        """
        Загружает отслеживаемые папки из БД
        и запускает Watchdog для каждой из них.
        """

        with SessionLocal() as session:
            folders = get_watched_folders(session)

            if not folders:
                print("Нет папок для отслеживания.")
                return

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
            f"Наблюдение запущено для {len(folders)} папок."
        )

    def stop(self):
        """
        Останавливает Watchdog.
        """

        self.observer.stop()
        self.observer.join()
