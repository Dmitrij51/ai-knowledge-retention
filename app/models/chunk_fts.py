from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.database import Base


class ChunkFTS(Base):
    """
    ORM-представление виртуальной FTS5-таблицы.
    """

    __tablename__ = "chunks_fts"

    rowid: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
