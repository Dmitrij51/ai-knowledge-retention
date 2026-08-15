from pathlib import Path


def parse_text(file_path: str) -> str:
    """
    Читает TXT-файл и возвращает его содержимое.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    if not path.is_file():
        raise ValueError(f"Это не файл: {file_path}")

    return path.read_text(encoding="utf-8")
