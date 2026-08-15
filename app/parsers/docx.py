from pathlib import Path

from docx import Document


def parse_docx(file_path: str) -> str:
    """
    Читает DOCX-файл и возвращает извлечённый текст.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    if not path.is_file():
        raise ValueError(f"Это не файл: {file_path}")

    document = Document(path)

    paragraphs = []

    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            paragraphs.append(paragraph.text)

    return "\n\n".join(paragraphs)
