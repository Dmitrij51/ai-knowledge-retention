from pathlib import Path

from app.parsers.text import parse_text
from app.parsers.markdown import parse_markdown
from app.parsers.pdf import parse_pdf
from app.parsers.docx import parse_docx


def load_document(file_path: str) -> str:
    """
    Определяет формат документа и использует
    соответствующий parser.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    if not path.is_file():
        raise ValueError(f"Это не файл: {file_path}")

    extension = path.suffix.lower()

    if extension == ".txt":
        return parse_text(file_path)

    if extension == ".md":
        return parse_markdown(file_path)

    if extension == ".pdf":
        return parse_pdf(file_path)

    if extension == ".docx":
        return parse_docx(file_path)

    raise ValueError(f"Неподдерживаемый формат файла: {extension}")
