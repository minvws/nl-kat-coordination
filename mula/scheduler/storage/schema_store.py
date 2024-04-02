from sqlalchemy import exc, func

from scheduler import models

from .filters import FilterRequest, apply_filter
from .storage import DBConn, retry


class SchemaStore:
    name: str = "schema_store"

    def __init__(self, dbconn: DBConn) -> None:
        self.dbconn = dbconn

    @retry()
    def get_schemas(
        self,
        schema_id: str | None = None,
        schema_hash: str | None = None,
        filters: FilterRequest | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[models.TaskSchema], int]:
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskSchemaDB)

            if schema_id is not None:
                query = query.filter(models.TaskSchemaDB.id == schema_id)

            if schema_hash is not None:
                query = query.filter(models.TaskSchemaDB.hash == schema_hash)

            if filters is not None:
                query = apply_filter(models.TaskSchemaDB, query, filters)

            try:
                count = query.count()
                tasks_orm = query.order_by(models.TaskSchemaDB.created_at.desc()).offset(offset).limit(limit).all()
            except exc.ProgrammingError as e:
                raise ValueError(f"Invalid filter: {e}") from e

            tasks = [models.TaskSchema.model_validate(task_orm) for task_orm in tasks_orm]

            return tasks, count

    @retry()
    def get_schema(self, task_id: str) -> models.TaskSchema:
        with self.dbconn.session.begin() as session:
            task_orm = session.query(models.TaskSchemaDB).filter(models.TaskSchemaDB.id == task_id).one_or_none()

            if task_orm is None:
                return None

            return models.TaskSchema.model_validate(task_orm)

    def get_schema_by_hash(self, schema_hash: str) -> models.TaskSchema:
        with self.dbconn.session.begin() as session:
            task_orm = session.query(models.TaskSchemaDB).filter(models.TaskSchemaDB.hash == schema_hash).one_or_none()

            if task_orm is None:
                return None

            return models.TaskSchema.model_validate(task_orm)

    @retry()
    def create_schema(self, task: models.TaskSchema) -> models.TaskSchema:
        with self.dbconn.session.begin() as session:
            task_orm = models.TaskSchemaDB(**task.model_dump())
            session.add(task_orm)

            created_task = models.TaskSchema.model_validate(task_orm)

            return created_task

    @retry()
    def update_schema(self, task: models.TaskSchema) -> models.TaskSchema:
        with self.dbconn.session.begin() as session:
            task_orm = session.query(models.TaskSchemaDB).filter(models.TaskSchemaDB.id == task.id).one_or_none()

            if task_orm is None:
                return None

            task_orm.update(task.model_dump())
            session.add(task_orm)

            # TODO: validate cron expression
            updated_task = models.TaskSchema.model_validate(task_orm)

            return updated_task
