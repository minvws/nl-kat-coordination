import time
import json
from functools import partial, wraps

from scheduler import models

from sqlalchemy import create_engine, orm, pool

from ..stores import Datastore  # noqa: TID252


class SQLAlchemy(Datastore):
    """SQLAlchemy datastore implementation

    Note on using sqlite:

    By default SQLite will only allow one thread to communicate with it,
    assuming that each thread would handle an independent request. This is to
    prevent accidentally sharing the same connection for different things (for
    different requests). But within the scheduler more than one thread could
    interact with the database. So we need to make SQLite know that it should
    allow that with

    Also, we will make sure each request gets its own database connection
    session.

    See: https://docs.sqlalchemy.org/en/14/dialects/sqlite.html#using-a-memory-database-in-multiple-threads
    """

    def __init__(self, dsn: str) -> None:
        super().__init__()

        self.engine = None

        serializer = partial(json.dumps, default=str)

        if dsn.startswith("sqlite"):
            self.engine = create_engine(
                dsn,
                connect_args={"check_same_thread": False},
                poolclass=pool.StaticPool,
                json_serializer=serializer,
            )
            models.Base.metadata.create_all(self.engine)
        else:
            self.engine = create_engine(
                dsn,
                pool_pre_ping=True,
                pool_size=25,
                pool_recycle=300,
                json_serializer=serializer,
            )

        if self.engine is None:
            raise Exception("Invalid datastore type")

        self.session = orm.sessionmaker(
            bind=self.engine,
        )


def retry(max_retries: int = 3, retry_delay: float = 5.):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if i == max_retries - 1:
                        raise e

                    print(f"Retrying {func.__name__} in {retry_delay} seconds ({i+1}/{max_retries}): {str(e)}")
                    time.sleep(retry_delay)

        return wrapper

    return decorator
