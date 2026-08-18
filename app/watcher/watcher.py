from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class FileWatcherHandler(FileSystemEventHandler):
    """
    Обрабатывает события файловой системы.
    """

    def on_created(self, event):
        if event.is_directory:
            return

        print(f"[CREATED] {event.src_path}")

    def on_modified(self, event):
        if event.is_directory:
            return

        print(f"[MODIFIED] {event.src_path}")

    def on_deleted(self, event):
        if event.is_directory:
            return

        print(f"[DELETED] {event.src_path}")

    def on_moved(self, event):
        if event.is_directory:
            return

        print(f"[MOVED] {event.src_path} -> {event.dest_path}")


def start_watcher(path: str):
    """
    Запускает наблюдение за папкой и всеми её подпапками.
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
