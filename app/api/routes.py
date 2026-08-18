from difflib import unified_diff

from fastapi import APIRouter, HTTPException, Query

from app.api.schemas import (
    DocumentResponse,
    DocumentVersionResponse,
    DocumentVersionsResponse,
    SearchResponse,
    SearchResult,
)
from app.search.service import SearchService
from app.storage.database import SessionLocal
from app.storage.documents import (
    get_document,
    get_documents,
)
from app.storage.file_versions import get_versions


router = APIRouter()

search_service = SearchService()


@router.get(
    "/search",
    response_model=SearchResponse,
)
def search(
    q: str = Query(
        ...,
        min_length=1,
        description="Поисковый запрос",
    ),
    limit: int = Query(
        5,
        ge=1,
        le=50,
        description="Количество результатов",
    ),
):
    """
    Выполняет hybrid search по базе знаний.
    """

    results = search_service.search(
        query=q,
        limit=limit,
    )

    return SearchResponse(
        query=q,
        results=[
            SearchResult(
                score=float(score),
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                content=chunk.content,
            )
            for score, chunk in results
        ],
    )


@router.get(
    "/documents",
    response_model=list[DocumentResponse],
)
def list_documents():
    """
    Возвращает все активные документы.
    """

    with SessionLocal() as session:
        documents = get_documents(session)

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


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
)
def get_document_by_id(document_id: int):
    """
    Возвращает активный документ по ID.
    """

    with SessionLocal() as session:
        document = get_document(
            session,
            document_id,
        )

        if document is None or document.is_deleted:
            raise HTTPException(
                status_code=404,
                detail="Документ не найден",
            )

        return DocumentResponse(
            id=document.id,
            filename=document.filename,
            path=document.path,
            file_type=document.file_type,
            file_hash=document.file_hash,
            is_deleted=document.is_deleted,
            created_at=document.created_at,
        )


@router.get(
    "/documents/{document_id}/versions",
    response_model=DocumentVersionsResponse,
)
def get_document_versions(document_id: int):
    """
    Возвращает историю всех версий документа.
    """

    with SessionLocal() as session:
        document = get_document(
            session,
            document_id,
        )

        if document is None:
            raise HTTPException(
                status_code=404,
                detail="Документ не найден",
            )

        versions = get_versions(
            session,
            document_id,
        )

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


@router.get(
    "/documents/{document_id}/versions/{version_number}",
    response_model=DocumentVersionResponse,
)
def get_document_version(
    document_id: int,
    version_number: int,
):
    """
    Возвращает конкретную версию документа.
    """

    if version_number <= 0:
        raise HTTPException(
            status_code=400,
            detail="Номер версии должен быть больше 0",
        )

    with SessionLocal() as session:
        document = get_document(
            session,
            document_id,
        )

        if document is None:
            raise HTTPException(
                status_code=404,
                detail="Документ не найден",
            )

        versions = get_versions(
            session,
            document_id,
        )

        version = next(
            (item for item in versions if item.version == version_number),
            None,
        )

        if version is None:
            raise HTTPException(
                status_code=404,
                detail="Версия не найдена",
            )

        return DocumentVersionResponse(
            id=version.id,
            document_id=version.document_id,
            version=version.version,
            file_hash=version.file_hash,
            content=version.content,
            created_at=version.created_at,
        )


@router.get(
    "/documents/{document_id}/versions/{version_number}/diff",
)
def get_document_version_diff(
    document_id: int,
    version_number: int,
):
    """
    Возвращает изменения между указанной версией
    и предыдущей версией.
    """

    if version_number <= 1:
        raise HTTPException(
            status_code=400,
            detail="Для первой версии Diff отсутствует",
        )

    with SessionLocal() as session:
        document = get_document(
            session,
            document_id,
        )

        if document is None:
            raise HTTPException(
                status_code=404,
                detail="Документ не найден",
            )

        versions = get_versions(
            session,
            document_id,
        )

        current_version = next(
            (item for item in versions if item.version == version_number),
            None,
        )

        previous_version = next(
            (item for item in versions if item.version == version_number - 1),
            None,
        )

        if current_version is None:
            raise HTTPException(
                status_code=404,
                detail="Версия не найдена",
            )

        if previous_version is None:
            raise HTTPException(
                status_code=404,
                detail="Предыдущая версия не найдена",
            )

        diff = list(
            unified_diff(
                previous_version.content.splitlines(),
                current_version.content.splitlines(),
                fromfile=f"version {previous_version.version}",
                tofile=f"version {current_version.version}",
                lineterm="",
            )
        )

        return {
            "document_id": document_id,
            "previous_version": previous_version.version,
            "current_version": current_version.version,
            "changed": previous_version.file_hash != current_version.file_hash,
            "diff": diff,
        }
