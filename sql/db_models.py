from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    Integer,
    UniqueConstraint,
    Table,
    Boolean,
)
from sqlalchemy.orm import relationship

from sql.db import SQL_BASE


organisation_repo_association_table = Table(
    "organisation_repository",
    SQL_BASE.metadata,
    Column("organisation_pk", ForeignKey("organisation.pk")),
    Column("repository_pk", ForeignKey("repository.pk")),
)


class OrganisationInDB(SQL_BASE):
    __tablename__ = "organisation"

    pk = Column(Integer, primary_key=True, autoincrement=True)
    id = Column(String(length=4), unique=True)
    name = Column(String(length=64), nullable=False)

    repositories = relationship(
        "RepositoryInDB", secondary=organisation_repo_association_table
    )


class RepositoryInDB(SQL_BASE):
    __tablename__ = "repository"

    pk = Column(Integer, primary_key=True, autoincrement=True)
    id = Column(String(length=32), unique=True)
    name = Column(String(length=64), nullable=False)
    base_url = Column(String(length=128), nullable=False)


class SettingInDB(SQL_BASE):
    __tablename__ = "setting"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(length=32), nullable=False)
    value = Column(String(length=64), nullable=False)
    organisation_pk = Column(
        Integer, ForeignKey("organisation.pk", ondelete="CASCADE"), nullable=False
    )

    organisation = relationship("OrganisationInDB")
    UniqueConstraint(
        "key", "organisation_id", name="unique_setting_keys_per_organisation"
    )


class PluginStateInDB(SQL_BASE):
    __tablename__ = "plugin_state"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plugin_id = Column(String(length=32), nullable=False)
    enabled = Column(Boolean, nullable=False)
    organisation_pk = Column(
        Integer, ForeignKey("organisation.pk", ondelete="CASCADE"), nullable=False
    )
    repository_pk = Column(
        Integer, ForeignKey("repository.pk", ondelete="CASCADE"), nullable=False
    )

    organisation = relationship("OrganisationInDB")
    repository = relationship("RepositoryInDB")
    UniqueConstraint(
        "plugin_id",
        "organisation_pk",
        "repository_pk",
        name="unique_plugin_per_repo_per_org",
    )
