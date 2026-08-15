from pathlib import Path

from pypdf import PdfReader


def parse_pdf(file_path: str) -> str:
    """
    Читает PDF-файл и возвращает извлечённый текст.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    if not path.is_file():
        raise ValueError(f"Это не файл: {file_path}")

    reader = PdfReader(path)

    pages = []

    for page in reader.pages:
        text = page.extract_text()

        if text:
            pages.append(text)

    return "\n\n".join(pages)