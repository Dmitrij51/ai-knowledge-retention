import numpy as np


def embedding_to_bytes(embedding: list[float]) -> bytes:
    return np.array(embedding, dtype=np.float32).tobytes()


def bytes_to_embedding(data: bytes) -> np.ndarray:
    return np.frombuffer(data, dtype=np.float32)

