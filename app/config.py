from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-small"

EMBEDDING_MODEL_PATH = BASE_DIR / "models" / "multilingual-e5-small"

EMBEDDING_DIMENSION = 384
