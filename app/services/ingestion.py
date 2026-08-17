from app.ai.embeddings import EmbeddingModel
from app.parsers.document_loader import load_document
from app.processing.cleaner import clean_text
from app.processing.chunker import split_text
from app.services.embeddings import EmbeddingService
from app.storage.database import SessionLocal
from app.storage.documents import create_document
from app.storage.chunks import create_chunks


def ingest_document(
    file_path: str,
) -> int:
    """
    Полный pipeline обработки документа:

    файл
    ↓
    parser
    ↓
    cleaner
    ↓
    chunker
    ↓
    Document + Chunks
    ↓
    embeddings
    ↓
    SQLite
    """

    # ---------------------------------
    # 1. Загружаем модель embeddings
    # ---------------------------------

    model = EmbeddingModel()

    embedding_service = EmbeddingService(model)

    # ---------------------------------
    # 2. Читаем документ
    # ---------------------------------

    raw_text = load_document(file_path)

    # ---------------------------------
    # 3. Очищаем текст
    # ---------------------------------

    text = clean_text(raw_text)

    if not text:
        raise ValueError("Документ не содержит текста")

    # ---------------------------------
    # 4. Разбиваем на chunks
    # ---------------------------------

    chunks = split_text(text)

    if not chunks:
        raise ValueError("Не удалось создать chunks")

    # ---------------------------------
    # 5. Открываем одну транзакцию
    # ---------------------------------

    with SessionLocal() as session:
        try:
            # Создаём Document
            document = create_document(
                session,
                file_path,
            )

            # Создаём Chunks
            chunk_objects = create_chunks(
                session,
                document.id,
                chunks,
            )

            # ---------------------------------
            # 6. Создаём embeddings
            # ---------------------------------

            for chunk in chunk_objects:
                try:
                    embedding_service.embed_chunk(chunk)

                except Exception as error:
                    print(f"Ошибка embedding для chunk {chunk.id}: {error}")

                    # Embedding оставляем NULL
                    chunk.embedding = None
                    chunk.embedding_model = None

            # ---------------------------------
            # 7. Сохраняем всё
            # ---------------------------------

            session.commit()

            return document.id

        except Exception:
            session.rollback()
            raise