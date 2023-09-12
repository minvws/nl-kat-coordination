import json
import logging
import time
from functools import partial, wraps

import sqlalchemy

logger = logging.getLogger(__name__)


class DBConn:
    def __init__(self, dsn: str) -> None:
        super().__init__()

        self.engine = None

        serializer = partial(json.dumps, default=str)

        self.engine = sqlalchemy.create_engine(
            dsn,
            pool_pre_ping=True,
            pool_size=25,
            pool_recycle=300,
            json_serializer=serializer,
        )

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
