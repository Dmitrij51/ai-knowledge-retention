from sentence_transformers import SentenceTransformer

from app.config import EMBEDDING_MODEL_PATH


class EmbeddingModel:
    def __init__(self):
        if not EMBEDDING_MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Embedding-модель не найдена:\n{EMBEDDING_MODEL_PATH}"
            )

        self.model = SentenceTransformer(str(EMBEDDING_MODEL_PATH))

    def embed_document(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("Cannot create embedding from empty document")

        embedding = self.model.encode(
            f"passage: {text}",
            normalize_embeddings=True,
        )

        return embedding.tolist()

    def embed_query(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("Cannot create embedding from empty query")

        embedding = self.model.encode(
            f"query: {text}",
            normalize_embeddings=True,
        )

        return embedding.tolist()
