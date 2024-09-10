from enum import Enum

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, UniqueConstraint, types
from sqlalchemy.orm import relationship

from boefjes.sql.db import SQL_BASE


class ScanLevel(Enum):
    L0 = 0
    L1 = 1
    L2 = 2
    L3 = 3
    L4 = 4


class OrganisationInDB(SQL_BASE):
    __tablename__ = "organisation"

    pk = Column(Integer, primary_key=True, autoincrement=True)
    id = Column(String(length=32), unique=True, nullable=False)
    name = Column(String(length=64), nullable=False)


class BoefjeConfigInDB(SQL_BASE):
    __tablename__ = "boefje_config"
    __table_args__ = (
        UniqueConstraint(
            "organisation_pk",
            "boefje_id",
            name="unique_boefje_config_per_organisation_per_boefje",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    settings = Column(String(length=512), nullable=False, server_default="{}")
    enabled = Column(Boolean, nullable=False, server_default="false")
    boefje_id = Column(Integer, ForeignKey("boefje.id", ondelete="CASCADE"), nullable=False)

    organisation_pk = Column(Integer, ForeignKey("organisation.pk", ondelete="CASCADE"), nullable=False)
    organisation = relationship("OrganisationInDB")


class NormalizerConfigInDB(SQL_BASE):
    __tablename__ = "normalizer_config"
    __table_args__ = (
        UniqueConstraint(
            "organisation_pk",
            "normalizer_id",
            name="unique_normalizer_config_per_organisation_per_normalizer",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    enabled = Column(Boolean, nullable=False, server_default="false")
    normalizer_id = Column(Integer, ForeignKey("normalizer.id", ondelete="CASCADE"), nullable=False)

    organisation_pk = Column(Integer, ForeignKey("organisation.pk", ondelete="CASCADE"), nullable=False)
    organisation = relationship("OrganisationInDB")


class BoefjeInDB(SQL_BASE):
    __tablename__ = "boefje"

    id = Column(types.Integer, primary_key=True, autoincrement=True)
    plugin_id = Column(types.String(length=64), nullable=False, unique=True)
    created = Column(types.DateTime(timezone=True), nullable=True)
    static = Column(Boolean, nullable=False, server_default="false")

    # Metadata
    name = Column(String(length=64), nullable=False)
    description = Column(types.Text, nullable=True)
    scan_level = Column(types.Enum(*[str(x.value) for x in ScanLevel], name="scan_level"), nullable=False, default="4")

    # Job specifications
    consumes = Column(types.ARRAY(types.String(length=128)), default=lambda: [], nullable=False)
    produces = Column(types.ARRAY(types.String(length=128)), default=lambda: [], nullable=False)
    schema = Column(types.JSON(), nullable=True)

    # Image specifications
    oci_image = Column(types.String(length=256), nullable=True)
    oci_arguments = Column(types.ARRAY(types.String(length=128)), default=lambda: [], nullable=False)
    version = Column(types.String(length=16), nullable=True)


class NormalizerInDB(SQL_BASE):
    __tablename__ = "normalizer"

    id = Column(types.Integer, primary_key=True, autoincrement=True)
    plugin_id = Column(types.String(length=64), nullable=False, unique=True)
    created = Column(types.DateTime(timezone=True), nullable=True)
    static = Column(Boolean, nullable=False, server_default="false")

    # Metadata
    name = Column(String(length=64), nullable=False)
    description = Column(types.Text, nullable=True)

    # Job specifications
    consumes = Column(types.ARRAY(types.String(length=128)), default=lambda: [], nullable=False)
    produces = Column(types.ARRAY(types.String(length=128)), default=lambda: [], nullable=False)
    version = Column(types.String(length=16), nullable=True)
