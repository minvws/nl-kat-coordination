from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from bytes.database.db import SQL_BASE


class BoefjeMetaInDB(SQL_BASE):  # type: ignore
    __tablename__ = "boefje_meta"

    id = Column(UUID, primary_key=True)
    boefje_id = Column(String(length=64), nullable=False)
    boefje_version = Column(String(length=16))
    organization = Column(String(length=32), nullable=False)
    input_ooi = Column(String(length=1024), nullable=True)
    arguments = Column(JSON, nullable=False, default=lambda: {})

    started_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))


Index("organization_boefje_id", BoefjeMetaInDB.organization, BoefjeMetaInDB.boefje_id)


class RawFileInDB(SQL_BASE):  # type: ignore
    __tablename__ = "raw_file"

    id = Column(UUID, primary_key=True)
    secure_hash = Column(String(length=256), nullable=True)
    hash_retrieval_link = Column(String(length=2048), nullable=True)

    boefje_meta_id = Column(UUID, ForeignKey("boefje_meta.id", ondelete="CASCADE"), nullable=False)
    boefje_meta = relationship("BoefjeMetaInDB")

    mime_types = Column(ARRAY(String(length=64)), default=lambda: [])


class NormalizerMetaInDB(SQL_BASE):  # type: ignore
    __tablename__ = "normalizer_meta"

    id = Column(UUID, primary_key=True)
    normalizer_id = Column(String(length=64), nullable=False)
    normalizer_version = Column(String(length=16))
    started_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))

    # To be phased out for backward compatibility with the boefjes: normalizers should run on raw files
    boefje_meta_id = Column(UUID, ForeignKey("boefje_meta.id", ondelete="CASCADE"), nullable=False)
    boefje_meta = relationship("BoefjeMetaInDB")

    # Nullable because of backward compatibility
    raw_file_id = Column(UUID, ForeignKey("raw_file.id", ondelete="CASCADE"), nullable=True)
    raw_file = relationship("RawFileInDB")
