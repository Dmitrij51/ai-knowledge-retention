from app.ai.embeddings import EmbeddingModel
from app.ai.vector import embedding_to_bytes
from app.models.chunk import Chunk


EMBEDDING_DIMENSION = 384
EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-small"


class EmbeddingService:
    def __init__(self, model: EmbeddingModel):
        self.model = model

    def create_embedding(self, text: str,) -> bytes:
        if not text.strip():
            raise ValueError("Cannot create embedding from empty text")

        embedding = self.model.embed_document(text)

        if len(embedding) != EMBEDDING_DIMENSION:
            raise ValueError(
                f"Unexpected embedding dimension: "
                f"{len(embedding)}. "
                f"Expected {EMBEDDING_DIMENSION}."
            )

        return embedding_to_bytes(embedding)
        

    def embed_chunk(
        self,
        chunk: Chunk,
    ) -> None:

        embedding = self.create_embedding(
            chunk.content
        )

        chunk.embedding = embedding
        chunk.embedding_model = EMBEDDING_MODEL_NAME