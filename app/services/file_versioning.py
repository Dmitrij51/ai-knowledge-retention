from pathlib import Path

from app.parsers.document_loader import load_document
from app.processing.diff import create_diff
from app.services.ingestion import ingest_document
from app.storage.database import SessionLocal
from app.storage.documents import get_document_by_path
from app.storage.file_hash import calculate_file_hash
from app.storage.file_versions import (
    create_file_version,
    get_latest_version,
)


# ================================================================
# INITIAL VERSION
# ================================================================


def create_initial_version(
    file_path: str,
) -> None:
    """
    Создаёт первую FileVersion для уже зарегистрированного
    документа.

    ВАЖНО:

    ingest_document() отвечает за:

        Document
        Chunks
        Embeddings

    create_initial_version() отвечает только за:

        FileVersion
    """

    path = Path(file_path).expanduser().resolve()

    if not path.exists() or not path.is_file():
        print(f"[VERSION SKIP] Файл не существует: {path}")
        return

    normalized_path = str(path)

    # ============================================================
    # 1. Hash
    # ============================================================

    try:
        file_hash = calculate_file_hash(normalized_path)

    except (OSError, PermissionError) as error:
        print(f"[VERSION ERROR] Не удалось вычислить hash: {path} | {error}")

        return

    # ============================================================
    # 2. Content
    # ============================================================

    try:
        content = load_document(normalized_path)

    except Exception as error:
        print(f"[VERSION ERROR] Не удалось прочитать файл: {path} | {error}")

        return

    if content is None or not content.strip():
        print(f"[VERSION SKIP] Файл пустой: {path}")

        return

    # ============================================================
    # 3. Document
    # ============================================================

    with SessionLocal() as session:
        document = get_document_by_path(
            session,
            normalized_path,
        )

        if document is None:
            print(f"[VERSION ERROR] Документ не найден в БД: {path}")

            return

        # ========================================================
        # 4. Проверяем существующие версии
        # ========================================================

        latest_version = get_latest_version(
            session,
            document.id,
        )

        if latest_version is not None:
            # -----------------------------------------------
            # Та же версия уже существует.
            # -----------------------------------------------

            if latest_version.file_hash == file_hash:
                print(
                    f"[VERSION SKIP] "
                    f"Версия уже существует: "
                    f"{path} | "
                    f"Version={latest_version.version}"
                )

                return

            # -----------------------------------------------
            # Теоретически это означает,
            # что FileVersion отстаёт от Document.
            #
            # Создаём следующую версию.
            # -----------------------------------------------

            print(
                f"[VERSION WARNING] "
                f"Для документа уже существует "
                f"версия {latest_version.version}, "
                f"но hash отличается."
            )

        # ========================================================
        # 5. Создаём FileVersion
        # ========================================================

        version = create_file_version(
            session=session,
            document_id=document.id,
            file_hash=file_hash,
            content=content,
        )

        session.commit()

        print(f"[VERSION] Создана версия: {path} | Version={version.version}")


# ================================================================
# FILE CHANGE
# ================================================================


def process_file_change(
    file_path: str,
) -> None:
    """
    Полностью обрабатывает изменение файла.

    Pipeline:

        файл изменился
              ↓
        hash
              ↓
        Document
              ↓
        FileVersion
              ↓
        сравнение hash
              ↓
        загрузка нового content
              ↓
        ingest_document()
              ↓
        новые chunks
              ↓
        новые embeddings
              ↓
        новая FileVersion
              ↓
        Diff

    ingest_document() выполняет восстановление
    soft-deleted Document автоматически.
    """

    path = Path(file_path).expanduser().resolve()

    if not path.exists():
        print(f"[CHANGE SKIP] Файл больше не существует: {path}")
        return

    if not path.is_file():
        return

    normalized_path = str(path)

    print(f"[CHANGE] Обработка изменения: {normalized_path}")

    # ============================================================
    # 1. Новый hash
    # ============================================================

    try:
        file_hash = calculate_file_hash(normalized_path)

    except (OSError, PermissionError) as error:
        print(f"[CHANGE ERROR] Не удалось вычислить hash: {path} | {error}")

        return

    # ============================================================
    # 2. Проверяем существующий Document
    # ============================================================

    with SessionLocal() as session:
        document = get_document_by_path(
            session,
            normalized_path,
        )

        # --------------------------------------------------------
        # Документ ещё не зарегистрирован.
        # --------------------------------------------------------

        if document is None:
            print(f"[CHANGE] Документ ещё не зарегистрирован: {path}")

            should_create_initial_version = True

            latest_version = None

        else:
            should_create_initial_version = False

            latest_version = get_latest_version(
                session,
                document.id,
            )

            # ----------------------------------------------------
            # Если FileVersion уже содержит этот hash,
            # реального изменения нет.
            # ----------------------------------------------------

            if latest_version is not None and latest_version.file_hash == file_hash:
                print(f"[CHANGE SKIP] Файл фактически не изменился: {path}")

                return

            # ----------------------------------------------------
            # Дополнительная проверка Document.
            #
            # Это защищает от ситуации, когда ingestion
            # уже произошёл, а FileVersion ещё нет.
            # ----------------------------------------------------

            if document.file_hash == file_hash and latest_version is None:
                print(
                    f"[CHANGE] "
                    f"Document уже содержит актуальный hash, "
                    f"но FileVersion отсутствует: "
                    f"{path}"
                )

    # ============================================================
    # 3. Загружаем новое содержимое
    # ============================================================

    try:
        content = load_document(normalized_path)

    except Exception as error:
        print(f"[CHANGE ERROR] Не удалось прочитать файл: {path} | {error}")

        return

    if content is None or not content.strip():
        print(f"[CHANGE SKIP] Файл не содержит текста: {path}")

        return

    # ============================================================
    # 4. Новый / восстановленный документ
    # ============================================================

    if should_create_initial_version:
        try:
            document_id = ingest_document(normalized_path)

        except Exception as error:
            print(f"[CHANGE ERROR] Не удалось проиндексировать файл: {path} | {error}")

            return

        create_initial_version(normalized_path)

        print(
            f"[CHANGE] Новый файл зарегистрирован: {path} | Document ID={document_id}"
        )

        return

    # ============================================================
    # 5. Изменённый существующий документ
    #
    # Сначала обновляем RAG.
    # ============================================================

    try:
        document_id = ingest_document(normalized_path)

    except Exception as error:
        print(f"[CHANGE ERROR] Не удалось переиндексировать файл: {path} | {error}")

        return

    # ============================================================
    # 6. После успешного ingestion
    #    создаём FileVersion + Diff
    # ============================================================

    with SessionLocal() as session:
        document = get_document_by_path(
            session,
            normalized_path,
        )

        if document is None:
            print(f"[CHANGE ERROR] После ingestion документ не найден: {path}")

            return

        if document.id != document_id:
            print(
                f"[CHANGE WARNING] "
                f"ID документа изменился: "
                f"{document_id} -> {document.id}"
            )

        # --------------------------------------------------------
        # Получаем последнюю версию заново.
        # --------------------------------------------------------

        latest_version = get_latest_version(
            session,
            document.id,
        )

        # --------------------------------------------------------
        # Защита от повторного события watchdog.
        # --------------------------------------------------------

        if latest_version is not None and latest_version.file_hash == file_hash:
            print(f"[CHANGE SKIP] Версия уже существует: {path}")

            return

        # --------------------------------------------------------
        # Создаём новую FileVersion.
        # --------------------------------------------------------

        new_version = create_file_version(
            session=session,
            document_id=document.id,
            file_hash=file_hash,
            content=content,
        )

        # --------------------------------------------------------
        # Создаём Diff.
        # --------------------------------------------------------

        if latest_version is not None:
            diff = create_diff(
                latest_version.content,
                new_version.content,
            )

            print(f"\n[VERSION] {path}")

            print(f"Version: {new_version.version}")

            print(f"Diff:\n{diff}")

        else:
            print(f"[VERSION] Создана первая версия: {path}")

        # --------------------------------------------------------
        # Commit
        # --------------------------------------------------------

        session.commit()

        print(f"[VERSION] Версия сохранена: {path} | Version={new_version.version}")

    print(f"[CHANGE] Файл полностью обновлён в Knowledge Base: {path}")
