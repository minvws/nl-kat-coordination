from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from boefjes.sql.db import SQL_BASE


class OrganisationInDB(SQL_BASE):
    __tablename__ = "organisation"

    pk = Column(Integer, primary_key=True, autoincrement=True)
    id = Column(String(length=32), unique=True, nullable=False)
    name = Column(String(length=64), nullable=False)


class SettingsInDB(SQL_BASE):
    __tablename__ = "settings"
    __table_args__ = (
        UniqueConstraint(
            "organisation_pk",
            "plugin_id",
            name="unique_settings_per_organisation_per_plugin",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    values = Column(String(length=512), nullable=False)
    plugin_id = Column(String(length=64), nullable=False)
    organisation_pk = Column(Integer, ForeignKey("organisation.pk", ondelete="CASCADE"), nullable=False)

    organisation = relationship("OrganisationInDB")


class PluginStateInDB(SQL_BASE):
    __tablename__ = "plugin_state"
    __table_args__ = (
        UniqueConstraint(
            "plugin_id",
            "organisation_pk",
            name="unique_plugin_id_per_org",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    plugin_id = Column(String(length=64), nullable=False)
    enabled = Column(Boolean, nullable=False)

    organisation_pk = Column(Integer, ForeignKey("organisation.pk", ondelete="CASCADE"), nullable=False)
    organisation = relationship("OrganisationInDB")
