from app.ai.embeddings import EmbeddingModel
from app.ai.vector import embedding_to_bytes
from app.storage.chunks import update_chunk_embedding



class EmbeddingService:
    def __init__(self):
        self.model = EmbeddingModel()

    def embed_chunk(self, chunk_id: int, content: str) -> None:
        embedding = self.model.embed_document(content)

        embedding_bytes = embedding_to_bytes(embedding)

        update_chunk_embedding(
            chunk_id,
            embedding_bytes
        )