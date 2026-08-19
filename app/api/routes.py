from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.ai.rag import RAGService
from app.api.schemas import (
    AskResponse,
    AskSource,
    DocumentResponse,
    DocumentVersionResponse,
    DocumentVersionsResponse,
    SearchResponse,
    SearchResult,
)
from app.models.document import Document
from app.storage.database import SessionLocal


router = APIRouter()

rag_service = RAGService()


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
        )

    search_results = []

    with SessionLocal() as session:
        for score, chunk in results:
            document = session.scalar(
                select(Document).where(Document.id == chunk.document_id)
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


@router.get(
    "/ask",
    response_model=AskResponse,
)
def ask(
    q: str = Query(
        ...,
        min_length=1,
        description="Вопрос к базе знаний",
    ),
):
    """
    Отвечает на вопрос пользователя
    на основе локальной базы знаний
    и возвращает понятные источники.
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
        )

    sources = []

    with SessionLocal() as session:
        for score, chunk in result.sources:
            document = session.scalar(
                select(Document).where(Document.id == chunk.document_id)
            )

            if document is None:
                continue

            sources.append(
                AskSource(
                    document=document.filename,
                    content=chunk.content,
                )
            )

    return AskResponse(
        question=q,
        answer=result.answer,
        sources=sources,
    )


@router.get(
    "/documents",
    response_model=list[DocumentResponse],
)
def get_documents():
    """
    Возвращает список документов в базе знаний.
    """

    with SessionLocal() as session:
        documents = session.scalars(select(Document)).all()

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
    "/documents/{document_id}/versions",
    response_model=DocumentVersionsResponse,
)
def get_document_versions(
    document_id: int,
):
    """
    Возвращает историю версий документа.
    """

    from app.models.document_version import DocumentVersion

    with SessionLocal() as session:
        document = session.scalar(select(Document).where(Document.id == document_id))

        if document is None:
            raise HTTPException(
                status_code=404,
                detail="Документ не найден",
            )

        versions = session.scalars(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version.desc())
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
