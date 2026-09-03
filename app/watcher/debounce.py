import threading
from pathlib import Path


class Debouncer:
    """
    Откладывает обработку файла до тех пор,
    пока файл не перестанет изменяться
    в течение указанного времени.
    """

    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.timers: dict[str, threading.Timer] = {}
        self.lock = threading.Lock()

    def call(self, file_path: str, callback):
        path = str(Path(file_path).resolve())

        with self.lock:
            old_timer = self.timers.get(path)

            if old_timer is not None:
                old_timer.cancel()

            timer = threading.Timer(
                self.delay,
                self._execute,
                args=(path, callback),
            )

            self.timers[path] = timer
            timer.start()

    def _execute(self, path: str, callback):
        try:
            callback(path)

        finally:
            with self.lock:
                self.timers.pop(path, None)

    def cancel(self, file_path: str):
        path = str(Path(file_path).resolve())

        with self.lock:
            timer = self.timers.pop(path, None)

            if timer is not None:
                timer.cancel()
