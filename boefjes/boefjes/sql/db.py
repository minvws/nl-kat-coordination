import logging
from functools import lru_cache
from typing import Any, Callable, Iterator, Type

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from boefjes.config import settings

logger = logging.getLogger(__name__)

SQL_BASE = declarative_base()


@lru_cache(maxsize=None)
def get_engine() -> Engine:
    """Returns database engine according to config settings."""
    db_uri = make_url(name_or_url=str(settings.katalogus_db_uri))
    db_uri_redacted = db_uri.render_as_string(hide_password=True)
    logger.info("Connecting to database %s with pool size %s...", db_uri_redacted, settings.db_connection_pool_size)

    engine = create_engine(url=db_uri, pool_pre_ping=True, pool_size=settings.db_connection_pool_size)

    logger.info("Connected to database %s", db_uri_redacted)

    return engine


def session_managed_iterator(service_factory: Callable[[Session], Any]) -> Iterator[Any]:
    """For FastApi-style managing of sessions life cycle within a request."""

    session = sessionmaker(bind=get_engine())()
    service = service_factory(session)

    try:
        yield service
    except Exception as error:
        logger.exception("An error occurred: %s. Rolling back session", error)
        session.rollback()
        raise error
    finally:
        logger.info("Closing session for %s", service.__class__)
        session.close()


class ObjectNotFoundException(Exception):
    def __init__(self, cls: Type[SQL_BASE], **kwargs):  # type: ignore
        super().__init__(f"The object of type {cls} was not found for query parameters {kwargs}")
