from typing import Generator
from sqlalchemy.orm import Session

from app.ai.rag import RAGService
from app.storage.database import SessionLocal
from app.watcher.manager import WatcherManager

# Менеджер папок
watcher_manager = WatcherManager()

# Ленивая инициализация RAGService
_rag_service: RAGService | None = None


def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


# DEPENDENCY ДЛЯ СЕССИИ БД
def get_db() -> Generator[Session, None, None]:
    """
    Создает сессию базы данных для каждого запроса
    и гарантированно закрывает её после завершения.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
