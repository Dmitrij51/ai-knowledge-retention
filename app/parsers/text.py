from pathlib import Path


def parse_text(file_path: str) -> str:
    """
    Читает TXT-файл.

    Пробует несколько распространённых кодировок:
    1. UTF-8 с BOM
    2. UTF-8
    3. UTF-16
    4. Windows-1251
    """

    path = Path(file_path)

    encodings = [
        "utf-8-sig",
        "utf-8",
        "utf-16",
        "cp1251",
    ]

    last_error = None

    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding)

        except UnicodeDecodeError as error:
            last_error = error

    raise UnicodeDecodeError(
        "unknown",
        b"",
        0,
        1,
        f"Не удалось определить кодировку файла: {path}. "
        f"Последняя ошибка: {last_error}",
    )
