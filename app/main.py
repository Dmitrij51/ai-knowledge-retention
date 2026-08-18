import time

from app.watcher.manager import WatcherManager


def main():
    manager = WatcherManager()

    try:
        count = manager.start()

        if count == 0:
            return

        print("Система запущена.")
        print("Наблюдение за файлами активно.")
        print("Для остановки нажми Ctrl+C")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nОстановка приложения...")

    finally:
        manager.stop()


if __name__ == "__main__":
    main()
