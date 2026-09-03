from pathlib import Path
from threading import Lock

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
    get_document_by_path_any,
    update_document,
)
from app.storage.file_hash import calculate_file_hash
from app.storage.chunks import (
    create_chunks,
    delete_document_chunks,
)


# ================================================================
# EMBEDDING MODEL
# ================================================================

_embedding_service: EmbeddingService | None = None
_embedding_lock = Lock()


def get_embedding_service() -> EmbeddingService:
    """
    Возвращает единственный экземпляр EmbeddingService.

    Embedding-модель загружается только один раз
    за время работы приложения.
    """

    global _embedding_service

    if _embedding_service is None:
        with _embedding_lock:
            if _embedding_service is None:
                print("[EMBEDDINGS] Загрузка embedding-модели...")

                model = EmbeddingModel()
                _embedding_service = EmbeddingService(model)

                print("[EMBEDDINGS] Embedding-модель загружена.")

    return _embedding_service


# ================================================================
# INGESTION
# ================================================================


def ingest_document(file_path: str) -> int:
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
        Document
          ↓
        Chunks
          ↓
        Embeddings
          ↓
        SQLite

    Существующий файл:

        файл
          ↓
        сравнение hash
          ↓
        если изменился:
            удалить старые chunks
            создать новые chunks
            создать embeddings
            обновить Document

    Soft-deleted файл:

        файл снова появился
          ↓
        найти Document по path
          ↓
        восстановить is_deleted=False
          ↓
        переиндексировать
          ↓
        сохранить историю версий

    Возвращает ID Document.
    """

    # ============================================================
    # 1. Проверяем путь
    # ============================================================

    path = Path(file_path).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(f"Файл не существует: {path}")

    if not path.is_file():
        raise ValueError(f"Указанный путь не является файлом: {path}")

    normalized_path = str(path)

    print(f"[INGEST] Обработка: {normalized_path}")

    # ============================================================
    # 2. Вычисляем SHA-256
    # ============================================================

    file_hash = calculate_file_hash(normalized_path)

    # ============================================================
    # 3. Загружаем документ
    # ============================================================

    raw_text = load_document(normalized_path)

    if raw_text is None:
        raise ValueError(f"Parser не вернул содержимое: {path}")

    # ============================================================
    # 4. Очищаем текст
    # ============================================================

    text = clean_text(raw_text)

    if not text or not text.strip():
        raise ValueError(f"Документ не содержит текста: {path}")

    # ============================================================
    # 5. Создаём chunks
    # ============================================================

    chunks = split_text(text)

    if not chunks:
        raise ValueError(f"Не удалось создать chunks: {path}")

    chunks = [chunk for chunk in chunks if chunk is not None and str(chunk).strip()]

    if not chunks:
        raise ValueError(f"После очистки не осталось chunks: {path}")

    print(f"[INGEST] Создано chunks: {len(chunks)}")

    # ============================================================
    # 6. Embedding service
    # ============================================================

    embedding_service = get_embedding_service()

    # ============================================================
    # 7. Работа с БД
    # ============================================================

    with SessionLocal() as session:
        try:
            # ====================================================
            # 7.1. Ищем активный документ по path
            # ====================================================

            document = get_document_by_path(
                session,
                normalized_path,
            )

            # ====================================================
            # СЦЕНАРИЙ A
            #
            # Активный документ существует.
            # ====================================================

            if document is not None:
                # ------------------------------------------------
                # Файл не изменился.
                # ------------------------------------------------

                if document.file_hash == file_hash:
                    print(
                        f"[INGEST] Файл не изменился: "
                        f"{document.filename} "
                        f"(ID={document.id})"
                    )

                    session.rollback()

                    return document.id

                # ------------------------------------------------
                # Файл изменился.
                # ------------------------------------------------

                print(
                    f"[INGEST] Файл изменён. "
                    f"Переиндексация: "
                    f"{document.filename} "
                    f"(ID={document.id})"
                )

                delete_document_chunks(
                    session,
                    document.id,
                )

                update_document(
                    session=session,
                    document=document,
                    file_hash=file_hash,
                    file_path=normalized_path,
                )

            # ====================================================
            # СЦЕНАРИЙ B
            #
            # Активного документа по path нет.
            # Проверяем soft-deleted Document.
            # ====================================================

            else:
                deleted_document = get_document_by_path_any(
                    session,
                    normalized_path,
                )

                if deleted_document is not None:
                    # ------------------------------------------------
                    # ВАЖНО:
                    #
                    # Не создаём новый Document.
                    #
                    # Восстанавливаем старый.
                    # ------------------------------------------------

                    print(
                        f"[INGEST] "
                        f"Восстановление удалённого документа: "
                        f"{deleted_document.filename} "
                        f"(ID={deleted_document.id})"
                    )

                    document = update_document(
                        session=session,
                        document=deleted_document,
                        file_hash=file_hash,
                        file_path=normalized_path,
                    )

                    # Старые chunks могут остаться от предыдущего
                    # состояния документа.
                    #
                    # Поэтому перед новой индексацией обязательно
                    # удаляем их.
                    delete_document_chunks(
                        session,
                        document.id,
                    )

                    print(f"[INGEST] Документ восстановлен: ID={document.id}")

                # ====================================================
                # СЦЕНАРИЙ C
                #
                # Документа по path вообще нет.
                # ====================================================

                else:
                    existing_by_hash = get_document_by_hash(
                        session,
                        file_hash,
                    )

                    if existing_by_hash is not None:
                        print(
                            f"[INGEST] "
                            f"Найден другой документ с таким же hash: "
                            f"{existing_by_hash.filename} "
                            f"(ID={existing_by_hash.id})"
                        )

                        print(
                            "[INGEST] "
                            f"Создаём отдельный Document для: "
                            f"{normalized_path}"
                        )

                    document = create_document(
                        session=session,
                        file_path=normalized_path,
                        file_hash=file_hash,
                    )

                    print(
                        f"[INGEST] "
                        f"Новый документ: "
                        f"{document.filename} "
                        f"(ID={document.id})"
                    )

            # ====================================================
            # 8. Создаём новые chunks
            # ====================================================

            chunk_objects = create_chunks(
                session=session,
                document_id=document.id,
                chunks=chunks,
            )

            if not chunk_objects:
                raise ValueError(f"create_chunks() не создал chunks: {path}")

            print(f"[INGEST] Chunks сохранены: {len(chunk_objects)}")

            # ====================================================
            # 9. Создаём embeddings
            # ====================================================

            for chunk in chunk_objects:
                try:
                    embedding_service.embed_chunk(chunk)

                except Exception as error:
                    raise RuntimeError(
                        f"Не удалось создать embedding для chunk {chunk.id}: {error}"
                    ) from error

            # ====================================================
            # 10. Проверяем embeddings
            # ====================================================

            for chunk in chunk_objects:
                if not chunk.embedding:
                    raise RuntimeError(f"Chunk {chunk.id} не содержит embedding")

            # ====================================================
            # 11. Commit
            # ====================================================

            session.commit()

            print(f"[INGEST] Готово: {path} | Document ID={document.id}")

            return document.id

        except Exception:
            session.rollback()

            print(f"[INGEST ERROR] Откат транзакции: {path}")

            raise
