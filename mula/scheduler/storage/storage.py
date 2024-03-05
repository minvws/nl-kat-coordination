import json
import logging
import time
from functools import partial, wraps

import sqlalchemy

from scheduler.config import settings

logger = logging.getLogger(__name__)


class DBConn:
    def __init__(self, dsn: str) -> None:
        super().__init__()

        self.engine = None

        serializer = partial(json.dumps, default=str)

        db_uri_redacted = sqlalchemy.engine.make_url(name_or_url=str(dsn)).render_as_string(hide_password=True)
        pool_size = settings.Settings().db_connection_pool_size

        logger.info("Connecting to database %s with pool size %s...", db_uri_redacted, pool_size)
        self.engine = sqlalchemy.create_engine(
            dsn,
            pool_pre_ping=True,
            pool_size=pool_size,
            pool_recycle=300,
            json_serializer=serializer,
        )
        logger.info("Connected to database %s.", db_uri_redacted)

        if self.engine is None:
            raise Exception("Invalid datastore type")

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
