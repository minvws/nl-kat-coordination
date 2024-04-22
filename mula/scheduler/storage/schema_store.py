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
                schemas_orm = query.order_by(models.TaskSchemaDB.created_at.desc()).offset(offset).limit(limit).all()
            except exc.ProgrammingError as e:
                raise ValueError(f"Invalid filter: {e}") from e

            schemas = [models.TaskSchema.model_validate(schema_orm) for schema_orm in schemas_orm]

            return schemas, count

    @retry()
    def get_schema(self, schema_id: str) -> models.TaskSchema:
        with self.dbconn.session.begin() as session:
            schema_orm = session.query(models.TaskSchemaDB).filter(models.TaskSchemaDB.id == schema_id).one_or_none()

            if schema_orm is None:
                return None

            return models.TaskSchema.model_validate(schema_orm)

    def get_schema_by_hash(self, schema_hash: str) -> models.TaskSchema:
        with self.dbconn.session.begin() as session:
            schema_orm = (
                session.query(models.TaskSchemaDB).filter(models.TaskSchemaDB.hash == schema_hash).one_or_none()
            )

            if schema_orm is None:
                return None

            return models.TaskSchema.model_validate(schema_orm)

    @retry()
    def create_schema(self, schema: models.TaskSchema) -> models.TaskSchema:
        with self.dbconn.session.begin() as session:
            schema_orm = models.TaskSchemaDB(**schema.model_dump())
            session.add(schema_orm)

            created_schema = models.TaskSchema.model_validate(schema_orm)

            return created_schema

    @retry()
    def update_schema(self, schema: models.TaskSchema) -> None:
        with self.dbconn.session.begin() as session:
            (
                session.query(models.TaskSchemaDB)
                .filter(models.TaskSchemaDB.id == schema.id)
                .update(schema.model_dump(exclude={"tasks"}))
            )

    @retry()
    def delete_schema(self, schema_id: str) -> None:
        with self.dbconn.session.begin() as session:
            session.query(models.TaskSchemaDB).filter(models.TaskSchemaDB.id == schema_id).delete()
