import numpy as np
from sqlalchemy import select

from app.ai.embeddings import EmbeddingModel
from app.ai.vector import bytes_to_embedding
from app.models.chunk import Chunk
from app.models.document import Document
from app.storage.database import SessionLocal


class SemanticSearch:
    """
    Семантический поиск по embeddings,
    сохранённым в SQLite.

    В поиск попадают только chunks активных документов.
    """

    MIN_CHUNK_LENGTH = 20

    def __init__(self, model: EmbeddingModel):
        self.model = model

    @staticmethod
    def cosine_similarity(
        a: np.ndarray,
        b: np.ndarray,
    ) -> float:
        """
        Вычисляет cosine similarity между двумя векторами.
        """

        a_norm = np.linalg.norm(a)
        b_norm = np.linalg.norm(b)

        if a_norm == 0 or b_norm == 0:
            return 0.0

        return float(np.dot(a, b) / (a_norm * b_norm))

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[tuple[float, Chunk]]:
        """
        Ищет наиболее похожие chunks по смыслу.

        Учитываются только:
        - chunks с embedding;
        - chunks активных документов;
        - chunks достаточного размера.
        """

        if not query.strip():
            return []

        if limit <= 0:
            raise ValueError("limit должен быть больше 0")

        # ---------------------------------
        # 1. Embedding запроса
        # ---------------------------------

        query_embedding = np.array(
            self.model.embed_query(query),
            dtype=np.float32,
        )

        with SessionLocal() as session:
            # ---------------------------------
            # 2. Получаем только активные chunks
            # ---------------------------------

            stmt = (
                select(Chunk)
                .join(
                    Document,
                    Chunk.document_id == Document.id,
                )
                .where(
                    Chunk.embedding.is_not(None),
                    Document.is_deleted.is_(False),
                )
            )

            chunks = session.scalars(stmt).all()

            results = []

            # ---------------------------------
            # 3. Сравниваем embeddings
            # ---------------------------------

            for chunk in chunks:
                # Игнорируем слишком маленькие chunks
                if not chunk.content:
                    continue

                if len(chunk.content.strip()) < self.MIN_CHUNK_LENGTH:
                    continue

                try:
                    embedding = bytes_to_embedding(chunk.embedding)

                    # Проверяем размер embedding
                    if len(embedding) != len(query_embedding):
                        continue

                    score = self.cosine_similarity(
                        query_embedding,
                        embedding,
                    )

                    results.append((score, chunk))

                except (TypeError, ValueError):
                    # Повреждённый embedding
                    # не должен ломать весь поиск.
                    continue

        # ---------------------------------
        # 4. Сортировка
        # ---------------------------------

        results.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return results[:limit]
