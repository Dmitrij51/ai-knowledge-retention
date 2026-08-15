


def split_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """
    Разбивает текст на небольшие части (chunks).

    chunk_size — максимальный размер одного chunk.
    overlap — количество символов, которые повторяются
    между соседними chunks.
    """

    if not text:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size должен быть больше 0")

    if overlap < 0:
        raise ValueError("overlap не может быть отрицательным")

    if overlap >= chunk_size:
        raise ValueError("overlap должен быть меньше chunk_size")

    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks