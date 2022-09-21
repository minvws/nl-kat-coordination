import abc
import json
import logging
from enum import Enum
from typing import List, Optional, Tuple, Union

from scheduler import models
from sqlalchemy import create_engine, orm, pool


class Datastore(abc.ABC):
    def __init__(self) -> None:
        self.logger: logging.Logger = logging.getLogger(__name__)

    @abc.abstractmethod
    def get_tasks(
        self,
        scheduler_id: Union[str, None],
        status: Union[str, None],
        offset: int = 0,
        limit: int = 100,
    ) -> Tuple[List[models.Task], int]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_task_by_id(self, task_id: str) -> Optional[models.Task]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_task_by_hash(self, task_hash: str) -> Optional[models.Task]:
        raise NotImplementedError

    @abc.abstractmethod
    def add_task(self, task: models.Task) -> Optional[models.Task]:
        raise NotImplementedError

    @abc.abstractmethod
    def update_task(self, task: models.Task) -> None:
        raise NotImplementedError


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

        if dsn.startswith("sqlite"):
            self.engine = create_engine(
                dsn,
                connect_args={"check_same_thread": False},
                poolclass=pool.StaticPool,
                json_serializer=lambda obj: json.dumps(obj, default=str),
            )
        else:
            self.engine = create_engine(
                dsn,
                pool_pre_ping=True,
                pool_size=25,
                json_serializer=lambda obj: json.dumps(obj, default=str),
            )

        models.Base.metadata.create_all(self.engine)

        # Within the methods below, we use the session context manager to
        # ensure that the session is closed
        self.session = orm.sessionmaker(
            bind=self.engine,
        )

    def get_tasks(
        self, scheduler_id: Union[str, None], status: Union[str, None], offset: int = 0, limit: int = 100
    ) -> Tuple[List[models.Task], int]:
        with self.session.begin() as session:
            query = session.query(models.TaskORM)

            if scheduler_id is not None:
                query = query.filter(models.TaskORM.scheduler_id == scheduler_id)

            if status is not None:
                query = query.filter(models.TaskORM.status == models.TaskStatus(status).name)

            count = query.count()

            tasks_orm = query.order_by(models.TaskORM.created_at.desc()).offset(offset).limit(limit).all()

            return [models.Task.from_orm(task_orm) for task_orm in tasks_orm], count

    def get_task_by_id(self, task_id: str) -> Optional[models.Task]:
        with self.session.begin() as session:
            task_orm = session.query(models.TaskORM).filter(models.TaskORM.id == task_id).first()

            if task_orm is None:
                return None

            return models.Task.from_orm(task_orm)

    def get_task_by_hash(self, task_hash: str) -> Optional[models.Task]:
        with self.session.begin() as session:
            task_orm = (
                session.query(models.TaskORM)
                .order_by(models.TaskORM.created_at.desc())
                .filter(models.TaskORM.hash == task_hash)
                .first()
            )

            if task_orm is None:
                return None

            return models.Task.from_orm(task_orm)

    def add_task(self, task: models.Task) -> Optional[models.Task]:
        with self.session.begin() as session:
            task_orm = models.TaskORM(**task.dict())
            session.add(task_orm)

            return models.Task.from_orm(task_orm)

    def update_task(self, task: models.Task) -> None:
        with self.session.begin() as session:
            session.query(models.TaskORM).filter_by(id=task.id).update(task.dict())
