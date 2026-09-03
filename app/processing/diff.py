import difflib


def create_diff(
    old_content: str,
    new_content: str,
) -> str:
    """
    Создаёт текстовый diff между двумя версиями файла.

    Возвращает unified diff.
    """

    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile="previous",
        tofile="current",
    )

    return "".join(diff)