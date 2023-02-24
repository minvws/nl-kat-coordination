import uuid

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import CHAR, TypeDecorator


class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's UUID type, otherwise uses
    CHAR(32), storing as stringified hex values.

    Source(s):
        - https://docs.sqlalchemy.org/en/13/core/custom_types.html#backend-agnostic-guid-type
        - https://github.com/yuval9313/fastapi-restful/blob/master/fastapi_restful/guid_type.py
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID())

        return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value

        if dialect.name == "postgresql":
            return str(value)

        if not isinstance(value, uuid.UUID):
            return f"{uuid.UUID(value).int:032x}"

        return f"{value.int:032x}"

    def process_result_value(self, value, dialect):
        if value is None:
            return value

        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(value)

        return value
