from app.ai.embeddings import EmbeddingModel
from app.parsers.document_loader import load_document
from app.processing.cleaner import clean_text
from app.processing.chunker import split_text
from app.services.embeddings import EmbeddingService
from app.storage.database import SessionLocal
from app.storage.documents import (
    create_document,
    get_document_by_hash,
    get_document_by_path,
    update_document,
)
from app.storage.file_hash import calculate_file_hash
from app.storage.chunks import (
    create_chunks,
    delete_document_chunks,
)


def ingest_document(
    file_path: str,
) -> int:
    """
    Полный pipeline обработки документа.

    Новый файл:
        файл
        ↓
        hash
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

    Изменённый файл:
        файл
        ↓
        новый hash
        ↓
        существующий Document
        ↓
        удалить старые chunks
        ↓
        создать новые chunks
        ↓
        embeddings
        ↓
        обновить hash
    """

    # ---------------------------------
    # 1. Вычисляем SHA-256 файла
    # ---------------------------------

    file_hash = calculate_file_hash(file_path)

    # ---------------------------------
    # 2. Загружаем модель embeddings
    # ---------------------------------

    model = EmbeddingModel()
    embedding_service = EmbeddingService(model)

    # ---------------------------------
    # 3. Читаем документ
    # ---------------------------------

    raw_text = load_document(file_path)

    # ---------------------------------
    # 4. Очищаем текст
    # ---------------------------------

    text = clean_text(raw_text)

    if not text:
        raise ValueError("Документ не содержит текста")

    # ---------------------------------
    # 5. Разбиваем на chunks
    # ---------------------------------

    chunks = split_text(text)

    if not chunks:
        raise ValueError("Не удалось создать chunks")

    # ---------------------------------
    # 6. Одна транзакция на весь pipeline
    # ---------------------------------

    with SessionLocal() as session:
        try:
            # ---------------------------------
            # 6.1. Проверяем полный дубликат
            # ---------------------------------

            existing_by_hash = get_document_by_hash(
                session,
                file_hash,
            )

            if existing_by_hash is not None:
                print(
                    f"Документ уже существует: "
                    f"{existing_by_hash.filename} "
                    f"(ID={existing_by_hash.id})"
                )

                return existing_by_hash.id

            # ---------------------------------
            # 6.2. Проверяем документ по пути
            # ---------------------------------

            existing_document = get_document_by_path(
                session,
                file_path,
            )

            if existing_document is not None:
                # Файл существует, но hash изменился.
                # Значит документ был изменён.

                document = existing_document

                print(
                    f"Документ изменён. "
                    f"Переиндексация: "
                    f"{document.filename} "
                    f"(ID={document.id})"
                )

                # Удаляем старые chunks
                delete_document_chunks(
                    session,
                    document.id,
                )

                # Обновляем hash
                update_document(
                    session,
                    document,
                    file_hash,
                )

            else:
                # ---------------------------------
                # 6.3. Создаём новый Document
                # ---------------------------------

                document = create_document(
                    session,
                    file_path,
                    file_hash,
                )

                print(
                    f"Новый документ: "
                    f"{document.filename} "
                    f"(ID={document.id})"
                )

            # ---------------------------------
            # 7. Создаём новые chunks
            # ---------------------------------

            chunk_objects = create_chunks(
                session,
                document.id,
                chunks,
            )

            # ---------------------------------
            # 8. Создаём embeddings
            # ---------------------------------

            for chunk in chunk_objects:
                try:
                    embedding_service.embed_chunk(chunk)

                except Exception as error:
                    print(
                        f"Ошибка embedding для chunk "
                        f"{chunk.id}: {error}"
                    )

                    chunk.embedding = None
                    chunk.embedding_model = None

            # ---------------------------------
            # 9. Сохраняем всё одной транзакцией
            # ---------------------------------

            session.commit()

            return document.id

        except Exception:
            session.rollback()
            raise

