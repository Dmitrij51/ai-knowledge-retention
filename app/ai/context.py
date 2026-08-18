from app.models.chunk import Chunk


class ContextBuilder:
    """
    Формирует контекст для RAG из найденных chunks.
    """

    def __init__(
        self,
        max_chunks: int = 5,
        max_chars: int = 8000,
    ):
        if max_chunks <= 0:
            raise ValueError("max_chunks должен быть больше 0")

        if max_chars <= 0:
            raise ValueError("max_chars должен быть больше 0")

        self.max_chunks = max_chunks
        self.max_chars = max_chars

    def build(
        self,
        results: list[tuple[float, Chunk]],
    ) -> str:
        """
        Превращает результаты поиска
        в текстовый контекст для LLM.
        """

        if not results:
            return ""

        parts = []
        total_chars = 0

        for index, (score, chunk) in enumerate(
            results[: self.max_chunks],
            start=1,
        ):
            text = chunk.content.strip()

            if not text:
                continue

            source = (
                f"Документ ID: {chunk.document_id}\n"
                f"Chunk ID: {chunk.id}\n"
                f"Релевантность: {score:.4f}"
            )

            part = f"[Источник {index}]\n{source}\n\n{text}"

            # Проверяем общий размер контекста
            if total_chars + len(part) > self.max_chars:
                remaining = self.max_chars - total_chars

                if remaining <= 0:
                    break

                part = part[:remaining]

            parts.append(part)

            total_chars += len(part)

            if total_chars >= self.max_chars:
                break

        return "\n\n---\n\n".join(parts)
