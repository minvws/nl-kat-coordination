import json
import time
from functools import partial, wraps

import sqlalchemy
import structlog

from scheduler.config import settings

from .errors import StorageError

logger = structlog.getLogger(__name__)


class DBConn:
    def __init__(self, dsn: str, pool_size: int = 25) -> None:
        self.logger: structlog.BoundLogger = structlog.getLogger(__name__)

        self.dsn: str = dsn
        self.pool_size: int = pool_size

    def connect(self) -> None:
        db_uri_redacted = sqlalchemy.engine.make_url(
            name_or_url=self.dsn,
        ).render_as_string(hide_password=True)

        pool_size = settings.Settings().db_connection_pool_size

        self.logger.debug(
            "Connecting to database %s with pool size %s...",
            self.dsn,
            pool_size,
            dsn=db_uri_redacted,
            pool_size=pool_size,
        )

        try:
            serializer = partial(json.dumps, default=str)
            self.engine = sqlalchemy.create_engine(
                self.dsn,
                pool_pre_ping=True,
                pool_size=pool_size,
                pool_recycle=300,
                json_serializer=serializer,
            )
        except sqlalchemy.exc.SQLAlchemyError as e:
            self.logger.error(
                "Failed to connect to database %s: %s",
                self.dsn,
                e,
                dsn=db_uri_redacted,
            )
            raise StorageError("Failed to connect to database.")

        self.logger.debug(
            "Connected to database %s.",
            db_uri_redacted,
            dsn=db_uri_redacted,
        )

        try:
            self.session = sqlalchemy.orm.sessionmaker(
                bind=self.engine,
            )
        except sqlalchemy.exc.SQLAlchemyError as e:
            self.logger.error(
                "Failed to create session: %s",
                e,
            )
            raise StorageError("Failed to create session.")


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
