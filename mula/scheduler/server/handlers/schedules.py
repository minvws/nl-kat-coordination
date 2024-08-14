import datetime
import uuid
from typing import Any

import fastapi
import pydantic
import structlog
from fastapi import status

from scheduler import context, models, schedulers, storage
from scheduler.server import serializers, utils


class ScheduleAPI:
    def __init__(
        self,
        api: fastapi.FastAPI,
        ctx: context.AppContext,
        s: dict[str, schedulers.Scheduler],
    ) -> None:
        self.logger: structlog.BoundLogger = structlog.getLogger(__name__)
        self.api = api
        self.ctx = ctx
        self.schedulers: dict[str, schedulers.Scheduler] = s

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

    def list(
        self,
        request: fastapi.Request,
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
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                detail="min_created_at must be less than max_created_at",
            )

        if (min_deadline_at is not None and max_deadline_at is not None) and min_deadline_at > max_deadline_at:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                detail="min_deadline_at must be less than max_deadline_at",
            )

        try:
            results, count = self.ctx.datastores.schedule_store.get_schedules(
                schedule_hash=schedule_hash,
                enabled=enabled,
                min_deadline_at=min_deadline_at,
                max_deadline_at=max_deadline_at,
                min_created_at=min_created_at,
                max_created_at=max_created_at,
                offset=offset,
                limit=limit,
            )
        except storage.filters.errors.FilterError as exc:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                detail=f"invalid filter(s) [exception: {exc}]",
            ) from exc
        except storage.errors.StorageError as exc:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"error occurred while accessing the database [exception: {exc}]",
            ) from exc
        except Exception as exc:
            self.logger.exception(exc)
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="failed to get schedules",
            ) from exc

        return utils.paginate(request, results, count, offset, limit)

    def create(self, schedule: serializers.ScheduleCreate) -> Any:
        try:
            new_schedule = models.Schedule(**schedule.dict())
        except pydantic.ValidationError as exc:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                detail=f"invalid schedule [exception: {exc}]",
            ) from exc
        except Exception as exc:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                detail=f"failed to create schedule [exception: {exc}]",
            ) from exc

        s = self.schedulers.get(new_schedule.scheduler_id)
        if s is None:
            raise fastapi.HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="scheduler not found",
            )

        # Validate data with task type of the scheduler
        try:
            instance = s.ITEM_TYPE.parse_obj(new_schedule.data)
        except pydantic.ValidationError as exc:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                detail=f"invalid task data [exception: {exc}]",
            ) from exc

        # Create hash for schedule with task type
        try:
            new_schedule.hash = instance.hash
        except Exception as exc:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                detail=f"failed to create hash for schedule [exception: {exc}]",
            ) from exc

        # Check if schedule with the same hash already exists
        try:
            schedule = self.ctx.datastores.schedule_store.get_schedule_by_hash(new_schedule.hash)
            if schedule is not None:
                raise fastapi.HTTPException(
                    status_code=fastapi.status.HTTP_409_CONFLICT,
                    detail="schedule with the same hash already exists",
                )
        except storage.errors.StorageError as exc:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"error occurred while accessing the database [exception: {exc}]",
            ) from exc

        try:
            self.ctx.datastores.schedule_store.create_schedule(new_schedule)
        except storage.errors.StorageError as exc:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                detail=f"error occurred while accessing the database [exception: {exc}]",
            ) from exc
        except Exception as exc:
            self.logger.exception(exc)
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"failed to create schedule [exception: {exc}]",
            ) from exc

        return new_schedule

    def get(self, schedule_id: uuid.UUID) -> Any:
        try:
            schedule = self.ctx.datastores.schedule_store.get_schedule(schedule_id)
        except storage.errors.StorageError as exc:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"error occurred while accessing the database [exception: {exc}]",
            ) from exc
        except Exception as exc:
            self.logger.exception(exc)
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"failed to get schedule [exception: {exc}]",
            ) from exc

        if schedule is None:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail="schedule not found",
            )

        return schedule

    def patch(self, schedule_id: uuid.UUID, schedule: serializers.SchedulePatch) -> Any:
        try:
            schedule_db = self.ctx.datastores.schedule_store.get_schedule(schedule_id)
        except storage.errors.StorageError as exc:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"error occurred while accessing the database [exception: {exc}]",
            ) from exc
        except Exception as exc:
            self.logger.exception(exc)
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"failed to get schedule [exception: {exc}]",
            ) from exc

        if schedule_db is None:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail="schedule not found",
            )

        patch_data = schedule.model_dump(exclude_unset=True)
        if len(patch_data) == 0:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                detail="no data to patch",
            )

        # Update schedule
        updated_schedule = schedule_db.model_copy(update=patch_data)

        # Validate schedule, model_copy() does not validate the model
        try:
            models.Schedule(**updated_schedule.dict())
        except pydantic.ValidationError as exc:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                detail=f"invalid schedule [exception: {exc}]",
            ) from exc
        except Exception as exc:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                detail=f"failed to update schedule [exception: {exc}]",
            ) from exc

        # Update schedule in database
        try:
            self.ctx.datastores.schedule_store.update_schedule(updated_schedule)
        except storage.errors.StorageError as exc:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"error occurred while accessing the database [exception: {exc}]",
            ) from exc
        except Exception as exc:
            self.logger.exception(exc)
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"failed to update schedule [exception: {exc}]",
            ) from exc

        return updated_schedule
