# ============================================================
# MODELS.PY
# Database models
# ============================================================

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Table
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text, text
from sqlalchemy.sql import func

from .database import Base


# ============================================================
# SENTENCE MODEL
# ============================================================

class Sentence(Base):

    __tablename__ = "sentences"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    kiswahili = Column(
        Text,
        nullable=False
    )

    # True only for sentences created by an uploaded/imported CSV.  Existing
    # installations are migrated with False so deleting a CSV cannot remove
    # legacy records that have no source metadata.
    is_uploaded = Column(Boolean, nullable=False, default=False, server_default=text("FALSE"))


sentence_sources = Table(
    "sentence_sources",
    Base.metadata,
    Column("sentence_id", ForeignKey("sentences.id", ondelete="CASCADE"), primary_key=True),
    Column("upload_id", ForeignKey("uploaded_csvs.id", ondelete="CASCADE"), primary_key=True),
)


# ============================================================
# RESPONSE MODEL
# ============================================================

class Response(Base):

    __tablename__ = "responses"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    kiswahili = Column(
        Text,
        nullable=False
    )

    kisukuma = Column(
        Text,
        nullable=False
    )

    participant_id = Column(
        String(100),
        nullable=False,
        index=True
    )

    tribe = Column(String(50), nullable=True, index=True)
    target_language = Column(String(50), nullable=True)


class Tribe(Base):
    __tablename__ = "tribes"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    language_code = Column(String(50), unique=True, nullable=False)
    image = Column(String(200), nullable=False)


class LanguageDataset(Base):
    __tablename__ = "language_datasets"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    source_language = Column(String(50), nullable=False)
    target_language = Column(String(50), nullable=False)
    filename = Column(String(150), nullable=False)


class UploadedCSV(Base):
    __tablename__ = "uploaded_csvs"

    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, nullable=False, server_default=func.now())
