from sentence_transformers import SentenceTransformer


MODEL_NAME = "intfloat/multilingual-e5-small"


class EmbeddingModel:
    def __init__(self):
        self.model = SentenceTransformer(MODEL_NAME)

    def embed_document(self, text: str) -> list[float]:
        text = f"passage: {text}"

        embedding = self.model.encode(
            text,
            normalize_embeddings=True
        )

        return embedding.tolist()

    def embed_query(self, text: str) -> list[float]:
        text = f"query: {text}"

        embedding = self.model.encode(
            text,
            normalize_embeddings=True
        )

        return embedding.tolist()
    