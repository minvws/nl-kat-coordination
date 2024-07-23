import json
import logging
import time
from functools import partial, wraps

import pydantic
import sqlalchemy
import structlog
from sqlalchemy.ext.declarative import declarative_base

from scheduler.config import settings

from .errors import StorageError

logger = structlog.getLogger(__name__)


class DBConn:
    def __init__(self, dsn: str, pool_size: int = 25) -> None:
        super().__init__()

        self.logger: structlog.BoundLogger = structlog.getLogger(__name__)

        self.engine = None
        self.session = None

        self.connect(dsn, pool_size)

    def connect(self, dsn: str, pool_size: int) -> None:
        db_uri_redacted = sqlalchemy.engine.make_url(
            name_or_url=str(dsn)
        ).render_as_string(hide_password=True)

        pool_size = settings.Settings().db_connection_pool_size

        self.logger.debug(
            "Connecting to database %s with pool size %s...",
            dsn,
            pool_size,
            dsn=db_uri_redacted,
            pool_size=pool_size,
        )

        serializer = partial(json.dumps, default=str)
        self.engine = sqlalchemy.create_engine(
            dsn,
            pool_pre_ping=True,
            pool_size=pool_size,
            pool_recycle=300,
            json_serializer=serializer,
        )
        self.logger.debug(
            "Connected to database %s.",
            db_uri_redacted,
            dsn=db_uri_redacted,
        )

        if self.engine is None:
            raise StorageError("Invalid datastore type")

        self.session = sqlalchemy.orm.sessionmaker(
            bind=self.engine,
        )


def retry(max_retries: int = 3, retry_delay: float = 5.0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (
                    sqlalchemy.exc.OperationalError,
                    sqlalchemy.exc.InternalError,
                ) as e:
                    if i == max_retries - 1:
                        raise e

                    logger.warning(
                        "Retrying %s.%s in %f seconds (%f): %s",
                        func.__module__,
                        func.__name__,
                        retry_delay,
                        i + 1 / max_retries,
                        e,
                    )
                    time.sleep(retry_delay)

        return wrapper

    return decorator
