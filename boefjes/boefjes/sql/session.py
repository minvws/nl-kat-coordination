import structlog
from psycopg2 import errors
from sqlalchemy import exc
from sqlalchemy.orm import Session
from typing_extensions import Self

from boefjes.storage.interfaces import IntegrityError, StorageError, UniqueViolation

logger = structlog.get_logger(__name__)


class SessionMixin:
    """
    This mixin makes a context manager out of a repository implementing it so session management is handled nicely.
    Example of usage:

    >>> with SomeSessionedStorage() as repo:
    >>>     repo.create(...)
    >>>     repo.create(...)
    >>>

    This will handle commits. Rollbacks and closing the session should be done outside this context.
    """

    def __init__(self, session: Session):
        self.session: Session = session

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: type[Exception], exc_value: str, exc_traceback: str) -> None:  # noqa: F841
        if exc_type is not None:
            logger.error("An error occurred: %s. Rolling back session", exc_value)
            self.session.rollback()

            return

        try:
            logger.debug("Committing session")
            self.session.commit()
        except exc.IntegrityError as e:
            if isinstance(e.orig, errors.UniqueViolation):
                raise UniqueViolation(str(e.orig))
            raise IntegrityError("An integrity error occurred") from e
        except exc.DatabaseError as e:
            raise StorageError("A storage error occurred") from e
        finally:
            if exc_type is not None or self.session.is_active:
                logger.debug("Committing failed, rolling back")
                self.session.rollback()
