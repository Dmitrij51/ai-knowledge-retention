from pathlib import Path
from typing import Annotated

import tkinter as tk
from tkinter import filedialog

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.rag import RAGService
from app.api.deps import get_db, get_rag_service, watcher_manager
from app.api.schemas import (
    AskResponse,
    AskSource,
    DocumentResponse,
    DocumentVersionResponse,
    DocumentVersionsResponse,
    SearchResponse,
    SearchResult,
    WatchedFolderCreate,
    WatchedFolderResponse,
)
from app.models.document import Document
from app.models.file_version import FileVersion
from app.models.watched_folder import WatchedFolder
from app.storage.watched_folders import get_watched_folders


router = APIRouter()


# ================================================================
# DEPENDENCIES
# ================================================================

DBSession = Annotated[Session, Depends(get_db)]
RAG = Annotated[RAGService, Depends(get_rag_service)]


# ================================================================
# HOME
# ================================================================


@router.get("/")
def home():
    """
    Главная страница приложения.
    """

    # .parent (api) -> .parent (app)
    index_file = Path(__file__).resolve().parent.parent / "web" / "index.html"

    if not index_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Файл web/index.html не найден по пути: {index_file}",
        )

    return FileResponse(index_file)


# ================================================================
# SEARCH
# ================================================================


@router.get(
    "/search",
    response_model=SearchResponse,
)
def search(
    rag_service: RAG,
    session: DBSession,
    q: str = Query(
        ...,
        min_length=1,
        description="Поисковый запрос",
    ),
    limit: int = Query(
        10,
        ge=1,
        le=50,
        description="Количество результатов",
    ),
):
    """
    Выполняет поиск по базе знаний.
    """

    try:
        results = rag_service.search_service.search(
            q,
            limit=limit,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    search_results: list[SearchResult] = []

    for score, chunk in results:
        document = session.scalar(
            select(Document).where(
                Document.id == chunk.document_id,
                Document.is_deleted.is_(False),
            )
        )

        if document is None:
            continue

        search_results.append(
            SearchResult(
                score=float(score),
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                content=chunk.content,
            )
        )

    return SearchResponse(
        query=q,
        results=search_results,
    )


# ================================================================
# ASK
# ================================================================


@router.get(
    "/ask",
    response_model=AskResponse,
)
def ask(
    rag_service: RAG,
    session: DBSession,
    q: str = Query(
        ...,
        min_length=1,
        description="Вопрос к базе знаний",
    ),
):
    """
    Отвечает на вопрос пользователя
    на основе локальной базы знаний.
    """

    try:
        result = rag_service.ask(
            question=q,
            limit=5,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    sources: list[AskSource] = []

    for score, chunk in result.sources:
        document = session.scalar(
            select(Document).where(
                Document.id == chunk.document_id,
                Document.is_deleted.is_(False),
            )
        )

        if document is None:
            continue

        sources.append(
            AskSource(
                document_id=document.id,
                document=document.filename,
                content=chunk.content,
            )
        )

    return AskResponse(
        question=q,
        answer=result.answer,
        sources=sources,
    )


# ================================================================
# DOCUMENT FILE
# ================================================================


@router.get(
    "/documents/{document_id}/file",
)
def open_document_file(
    document_id: int,
    session: DBSession,
):
    """
    Открывает физический файл документа.
    """

    document = session.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.is_deleted.is_(False),
        )
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Активный документ не найден",
        )

    file_path = Path(document.path)

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Файл не найден на диске",
        )

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Путь документа не является файлом",
        )

    return FileResponse(
        file_path,
        filename=document.filename,
    )


# ================================================================
# DOCUMENTS
# ================================================================


@router.get(
    "/documents",
    response_model=list[DocumentResponse],
)
def get_documents(
    session: DBSession,
):
    """
    Возвращает активные документы базы знаний.

    Soft-deleted документы здесь не возвращаются.
    """

    documents = session.scalars(
        select(Document)
        .where(
            Document.is_deleted.is_(False),
        )
        .order_by(Document.id)
    ).all()

    return [
        DocumentResponse(
            id=document.id,
            filename=document.filename,
            path=document.path,
            file_type=document.file_type,
            file_hash=document.file_hash,
            is_deleted=document.is_deleted,
            created_at=document.created_at,
        )
        for document in documents
    ]


# ================================================================
# DOCUMENT VERSIONS
# ================================================================


@router.get(
    "/documents/{document_id}/versions",
    response_model=DocumentVersionsResponse,
)
def get_document_versions(
    document_id: int,
    session: DBSession,
):
    """
    Возвращает историю версий документа.
    """

    document = session.scalar(
        select(Document).where(
            Document.id == document_id,
        )
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Документ не найден",
        )

    versions = session.scalars(
        select(FileVersion)
        .where(
            FileVersion.document_id == document_id,
        )
        .order_by(FileVersion.version)
    ).all()

    return DocumentVersionsResponse(
        document_id=document_id,
        versions=[
            DocumentVersionResponse(
                id=version.id,
                document_id=version.document_id,
                version=version.version,
                file_hash=version.file_hash,
                content=version.content,
                created_at=version.created_at,
            )
            for version in versions
        ],
    )


# ================================================================
# WATCHED FOLDERS
# ================================================================


@router.get(
    "/watched-folders",
    response_model=list[WatchedFolderResponse],
)
def get_watched_folders_api(
    session: DBSession,
):
    """
    Возвращает все папки, зарегистрированные
    в системе наблюдения.
    """

    folders = get_watched_folders(session)

    return [
        WatchedFolderResponse(
            id=folder.id,
            path=folder.path,
            enabled=folder.enabled,
            created_at=folder.created_at,
        )
        for folder in folders
    ]


# ================================================================
# ADD WATCHED FOLDER
# ================================================================


@router.post(
    "/watched-folders",
    response_model=WatchedFolderResponse,
    status_code=201,
)
def add_watched_folder_api(
    data: WatchedFolderCreate,
    session: DBSession,
):
    """
    Добавляет папку в систему наблюдения.
    """

    try:
        folder_id = watcher_manager.add_folder(
            data.path,
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except NotADirectoryError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Не удалось добавить папку: {exc}",
        ) from exc

    folder = session.get(
        WatchedFolder,
        folder_id,
    )

    if folder is None:
        raise HTTPException(
            status_code=500,
            detail="Папка была добавлена, но не найдена в БД",
        )

    return WatchedFolderResponse(
        id=folder.id,
        path=folder.path,
        enabled=folder.enabled,
        created_at=folder.created_at,
    )


# ================================================================
# RESCAN FOLDER
# ================================================================


@router.post(
    "/watched-folders/{folder_id}/rescan",
)
def rescan_watched_folder(
    folder_id: int,
):
    """
    Повторно сканирует папку.
    """

    try:
        processed = watcher_manager.rescan_folder(
            folder_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except NotADirectoryError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {
        "folder_id": folder_id,
        "processed": processed,
    }


# ================================================================
# ENABLE FOLDER
# ================================================================


@router.post(
    "/watched-folders/{folder_id}/enable",
)
def enable_watched_folder(
    folder_id: int,
):
    """
    Включает наблюдение за папкой.
    """

    try:
        watcher_manager.enable_folder(
            folder_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except NotADirectoryError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {
        "folder_id": folder_id,
        "enabled": True,
    }


# ================================================================
# DISABLE FOLDER
# ================================================================


@router.post(
    "/watched-folders/{folder_id}/disable",
)
def disable_watched_folder(
    folder_id: int,
):
    """
    Отключает наблюдение за папкой.
    """

    try:
        watcher_manager.disable_folder(
            folder_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    return {
        "folder_id": folder_id,
        "enabled": False,
    }


# ================================================================
# DELETE WATCHED FOLDER
# ================================================================


@router.delete(
    "/watched-folders/{folder_id}",
)
def delete_watched_folder(
    folder_id: int,
):
    """
    Удаляет папку из списка наблюдения.
    """

    try:
        watcher_manager.delete_folder(
            folder_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    return {
        "folder_id": folder_id,
        "deleted": True,
    }


@router.get("/choose-folder")
def choose_folder():
    """
    Открывает системный диалог выбора папки.
    """

    root = None

    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        folder = filedialog.askdirectory(title="Выберите папку базы знаний")

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Не удалось открыть окно выбора папки: {exc}",
        ) from exc

    finally:
        if root is not None:
            root.destroy()

    if not folder:
        return {
            "selected": False,
            "path": None,
        }

    path = Path(folder).resolve()

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Выбранная папка не существует",
        )

    if not path.is_dir():
        raise HTTPException(
            status_code=400,
            detail="Выбранный путь не является папкой",
        )

    return {
        "selected": True,
        "path": str(path),
    }
