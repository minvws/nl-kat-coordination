import datetime
import uuid
from typing import Any

import fastapi
import structlog
from fastapi import Body

from scheduler import context, models, schedulers, storage
from scheduler.server import serializers, utils
from scheduler.server.errors import BadRequestError, ConflictError, NotFoundError, ValidationError


class ScheduleAPI:
    def __init__(
        self, api: fastapi.FastAPI, ctx: context.AppContext, schedulers: dict[str, schedulers.Scheduler]
    ) -> None:
        self.logger: structlog.BoundLogger = structlog.get_logger(__name__)
        self.api = api
        self.ctx = ctx
        self.schedulers = schedulers

        self.api.add_api_route(
            path="/schedules",
            endpoint=self.list,
            methods=["GET"],
            response_model=utils.PaginatedResponse,
            status_code=200,
            description="List all schedules",
        )

        self.api.add_api_route(
            path="/schedules",
            endpoint=self.create,
            methods=["POST"],
            response_model=models.Schedule,
            status_code=201,
            description="Create a schedule",
        )

        self.api.add_api_route(
            path="/schedules/{schedule_id}",
            endpoint=self.get,
            methods=["GET"],
            response_model=models.Schedule,
            status_code=200,
            description="Get a schedule",
        )

        self.api.add_api_route(
            path="/schedules/{schedule_id}",
            endpoint=self.patch,
            methods=["PATCH"],
            response_model=models.Schedule,
            response_model_exclude_unset=True,
            status_code=200,
            description="Update a schedule",
        )

        self.api.add_api_route(
            path="/schedules/{schedule_id}",
            endpoint=self.delete,
            methods=["DELETE"],
            status_code=204,
            description="Delete a schedule",
        )

        self.api.add_api_route(
            path="/schedules/search",
            endpoint=self.search,
            methods=["POST"],
            response_model=utils.PaginatedResponse,
            status_code=200,
            description="Search schedules",
        )

    def list(
        self,
        request: fastapi.Request,
        scheduler_id: str | None = None,
        schedule_hash: str | None = None,
        enabled: bool | None = None,
        offset: int = 0,
        limit: int = 10,
        min_deadline_at: datetime.datetime | None = None,
        max_deadline_at: datetime.datetime | None = None,
        min_created_at: datetime.datetime | None = None,
        max_created_at: datetime.datetime | None = None,
    ) -> Any:
        if (min_created_at is not None and max_created_at is not None) and min_created_at > max_created_at:
            raise BadRequestError("min_created_at must be less than max_created_at")

        if (min_deadline_at is not None and max_deadline_at is not None) and min_deadline_at > max_deadline_at:
            raise BadRequestError("min_deadline_at must be less than max_deadline_at")

        results, count = self.ctx.datastores.schedule_store.get_schedules(
            scheduler_id=scheduler_id,
            schedule_hash=schedule_hash,
            enabled=enabled,
            min_deadline_at=min_deadline_at,
            max_deadline_at=max_deadline_at,
            min_created_at=min_created_at,
            max_created_at=max_created_at,
            offset=offset,
            limit=limit,
        )

        return utils.paginate(request, results, count, offset, limit)

    def create(self, schedule: serializers.ScheduleCreate) -> Any:
        try:
            new_schedule = models.Schedule(**schedule.model_dump())
        except ValueError:
            raise ValidationError("validation error")

        s = self.schedulers.get(new_schedule.scheduler_id)
        if s is None:
            raise BadRequestError(f"Scheduler {new_schedule.scheduler_id} not found")

        # Validate data with task type of the scheduler
        try:
            instance = s.ITEM_TYPE.model_validate(new_schedule.data)
        except ValueError:
            raise BadRequestError("validation error")

        # Create hash for schedule with task type
        new_schedule.hash = instance.hash

        # Check if schedule with the same hash already exists
        schedule = self.ctx.datastores.schedule_store.get_schedule_by_hash(new_schedule.hash)
        if schedule is not None:
            raise ConflictError(f"schedule with the same hash already exists: {new_schedule.hash}")

        self.ctx.datastores.schedule_store.create_schedule(new_schedule)
        return new_schedule

    def get(self, schedule_id: uuid.UUID) -> Any:
        schedule = self.ctx.datastores.schedule_store.get_schedule(schedule_id)
        if schedule is None:
            raise NotFoundError(f"schedule not found, by schedule_id: {schedule_id}")

        return schedule

    def patch(self, schedule_id: uuid.UUID, schedule: serializers.SchedulePatch) -> Any:
        schedule_db = self.ctx.datastores.schedule_store.get_schedule(schedule_id)
        if schedule_db is None:
            raise NotFoundError(f"schedule not found, by schedule_id: {schedule_id}")

        patch_data = schedule.model_dump(exclude_unset=True)
        if len(patch_data) == 0:
            raise BadRequestError("no data to patch")

        # Update schedule
        updated_schedule = schedule_db.model_copy(update=patch_data)

        # Validate schedule, model_copy() does not validate the model
        try:
            models.Schedule(**updated_schedule.dict())
        except ValueError:
            raise ValidationError("validation error")

        # Update schedule in database
        self.ctx.datastores.schedule_store.update_schedule(updated_schedule)

        return updated_schedule

    def search(
        self,
        request: fastapi.Request,
        offset: int = 0,
        limit: int = 10,
        filters: storage.filters.FilterRequest | None = Body(...),
    ) -> utils.PaginatedResponse:
        if filters is None:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_400_BAD_REQUEST, detail="missing search filters"
            )

        try:
            results, count = self.ctx.datastores.schedule_store.get_schedules(
                offset=offset, limit=limit, filters=filters
            )
        except storage.filters.errors.FilterError as exc:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_400_BAD_REQUEST, detail=f"invalid filter(s) [exception: {exc}]"
            ) from exc
        except storage.errors.StorageError as exc:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"error occurred while accessing the database [exception: {exc}]",
            ) from exc
        except Exception as exc:
            self.logger.exception(exc)
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR, detail="failed to search schedules"
            ) from exc

        return utils.paginate(request, results, count, offset, limit)

    def delete(self, schedule_id: uuid.UUID) -> None:
        self.ctx.datastores.schedule_store.delete_schedule(schedule_id)
        return None
