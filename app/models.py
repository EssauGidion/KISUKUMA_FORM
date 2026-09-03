# ============================================================
# MODELS.PY
# Database models
# ============================================================

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text

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
