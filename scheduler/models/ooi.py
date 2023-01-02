import datetime
from enum import Enum as _Enum
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Column, DateTime, String

from .base import Base
from .scan_profile import ScanProfile


class OOI(BaseModel):
    """Representation of "Object Of Interests" from Octopoes."""

    primary_key: str
    object_type: str
    scan_profile: ScanProfile
    organisation_id: Optional[str]

    checked_at: Optional[datetime.datetime] = Field(default=None)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    modified_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    class Config:
        orm_mode = True

    def __hash__(self):
        return hash((self.primary_key, self.organisation_id))


class OOIORM(Base):
    """A SQLAlchemy datastore model respresentation of an OOI, this is
    specifically done for BoefjeSchedulers to keep track of the OOI's
    that have been and are being scanned.
    """

    __tablename__ = "oois"

    primary_key = Column(String, primary_key=True)
    object_type = Column(String)
    scan_profile = Column(JSON)
    organisation_id = Column(String)

    # Should allow nullable, because when null it didn't get checked
    checked_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    modified_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.datetime.utcnow,
    )


class MutationOperationType(_Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class ScanProfileMutation(BaseModel):
    operation: MutationOperationType
    primary_key: str
    value: Optional[OOI]
