from datetime import datetime

from pydantic import BaseModel, Field


# ================================================================
# SEARCH
# ================================================================


class SearchResult(BaseModel):
    score: float
    chunk_id: int
    document_id: int
    content: str


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]


# ================================================================
# ASK
# ================================================================


class AskSource(BaseModel):
    document_id: int
    document: str
    content: str


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: list[AskSource]


# ================================================================
# DOCUMENTS
# ================================================================


class DocumentResponse(BaseModel):
    id: int
    filename: str
    path: str
    file_type: str
    file_hash: str | None
    is_deleted: bool
    created_at: datetime


# ================================================================
# FILE VERSIONS
# ================================================================


class DocumentVersionResponse(BaseModel):
    id: int
    document_id: int
    version: int
    file_hash: str
    content: str
    created_at: datetime


class DocumentVersionsResponse(BaseModel):
    document_id: int
    versions: list[DocumentVersionResponse]


# ================================================================
# WATCHED FOLDERS
# ================================================================


class WatchedFolderCreate(BaseModel):
    path: str = Field(
        ...,
        min_length=1,
        description="Абсолютный или относительный путь к папке",
    )


class WatchedFolderResponse(BaseModel):
    id: int
    path: str
    enabled: bool
    created_at: datetime
