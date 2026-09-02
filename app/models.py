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
