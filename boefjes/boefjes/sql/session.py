import logging

from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import Session

from boefjes.katalogus.storage.interfaces import StorageError

logger = logging.getLogger(__name__)


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

    def __enter__(self) -> "SessionMixin":
        return self

    def __exit__(self, exc_type: type[Exception], exc_value: str, exc_traceback: str) -> None:  # noqa: F841
        if exc_type is not None:
            logger.error("An error occurred: %s. Rolling back session", exc_value, exc_info=True)
            self.session.rollback()

            return

        error = None

        try:
            logger.info("Committing session")
            self.session.commit()
        except DatabaseError as e:
            error = e
            logger.exception("Committing failed, rolling back")
            self.session.rollback()

        if error:
            raise StorageError("A storage error occurred") from error
