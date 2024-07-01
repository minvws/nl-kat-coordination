from typing import Any

import fastapi
import structlog
from fastapi import status

from scheduler import context, models, queues, schedulers, storage

from .. import serializers, utils


class SchedulerAPI:
    def __init__(
        self,
        api: fastapi.FastAPI,
        ctx: context.AppContext,
        s: dict[str, schedulers.Scheduler],
    ) -> None:
        self.logger: structlog.BoundLogger = structlog.getLogger(__name__)
        self.api: fastapi.FastAPI = api
        self.ctx: context.AppContext = ctx
        self.schedulers: dict[str, schedulers.Scheduler] = s

        self.api.add_api_route(
            path="/schedulers",
            endpoint=self.list_schedulers,
            methods=["GET"],
            response_model=list[models.Scheduler],
            status_code=status.HTTP_200_OK,
            description="List all schedulers",
        )

        self.api.add_api_route(
            path="/schedulers/{scheduler_id}",
            endpoint=self.get_scheduler,
            methods=["GET"],
            response_model=models.Scheduler,
            status_code=status.HTTP_200_OK,
            description="Get a scheduler",
        )

        self.api.add_api_route(
            path="/schedulers/{scheduler_id}",
            endpoint=self.patch_scheduler,
            methods=["PATCH"],
            response_model=models.Scheduler,
            status_code=status.HTTP_200_OK,
            description="Update a scheduler",
        )

        # FIXME
        # self.api.add_api_route(
        #     path="/schedulers/{scheduler_id}/tasks",
        #     endpoint=self.list_tasks,
        #     methods=["GET"],
        #     response_model=PaginatedResponse,
        #     status_code=status.HTTP_200_OK,
        #     description="List all tasks for a scheduler",
        # )

        self.api.add_api_route(
            path="/queues",
            endpoint=self.list_queues,
            methods=["GET"],
            response_model=list[models.Queue],
            response_model_exclude_unset=True,
            status_code=status.HTTP_200_OK,
            description="List all queues",
        )

        self.api.add_api_route(
            path="/queues/{queue_id}",
            endpoint=self.get_queue,
            methods=["GET"],
            response_model=models.Queue,
            status_code=status.HTTP_200_OK,
            description="Get a queue",
        )

        self.api.add_api_route(
            path="/queues/{queue_id}/pop",
            endpoint=self.pop_queue,
            methods=["POST"],
            response_model=models.Task | None,
            status_code=status.HTTP_200_OK,
            description="Pop an item from a queue",
        )

        self.api.add_api_route(
            path="/queues/{queue_id}/push",
            endpoint=self.push_queue,
            methods=["POST"],
            response_model=models.Task | None,
            status_code=status.HTTP_201_CREATED,
            description="Push an item to a queue",
        )

    def list_schedulers(self) -> Any:
        return [models.Scheduler(**s.dict()) for s in self.schedulers.values()]

    def get_scheduler(self, scheduler_id: str) -> Any:
        s = self.schedulers.get(scheduler_id)
        if s is None:
            raise fastapi.HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="scheduler not found",
            )

        return models.Scheduler(**s.dict())

    def patch_scheduler(self, scheduler_id: str, item: models.Scheduler) -> Any:
        s = self.schedulers.get(scheduler_id)
        if s is None:
            raise fastapi.HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="scheduler not found",
            )

        stored_scheduler_model = models.Scheduler(**s.dict())
        patch_data = item.model_dump(exclude_unset=True)
        if len(patch_data) == 0:
            raise fastapi.HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="no data to patch",
            )

        updated_scheduler = stored_scheduler_model.model_copy(update=patch_data)

        # We update the patched attributes, since the schedulers are kept
        # in memory.
        for attr, value in patch_data.items():
            try:
                setattr(s, attr, value)
            except AttributeError as exc:
                raise fastapi.HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="attribute not found",
                ) from exc

        # Enable or disable the scheduler if needed.
        if updated_scheduler.enabled:
            s.enable()
        elif not updated_scheduler.enabled:
            s.disable()

        return updated_scheduler

    def list_queues(self) -> Any:
        return [
            models.Queue(**s.queue.dict(include_pq=False))
            for s in self.schedulers.copy().values()
        ]

    def get_queue(self, queue_id: str) -> Any:
        s = self.schedulers.get(queue_id)
        if s is None:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail="scheduler not found, by queue_id",
            )

        q = s.queue
        if q is None:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail="queue not found",
            )

        return models.Queue(**q.dict())

    def pop_queue(
        self, queue_id: str, filters: storage.filters.FilterRequest | None = None
    ) -> Any:
        s = self.schedulers.get(queue_id)
        if s is None:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail="queue not found",
            )

        try:
            p_item = s.pop_item_from_queue(filters)
        except queues.QueueEmptyError:
            return None

        if p_item is None:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail="could not pop item from queue, check your filters",
            )

        return models.Task(**p_item.model_dump())

    def push_queue(self, queue_id: str, item_in: serializers.Task) -> Any:
        s = self.schedulers.get(queue_id)
        if s is None:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail="queue not found",
            )

        try:
            # Load default values
            default_item = models.Task()
            patch_data = item_in.model_dump(exclude_unset=True)
            new_item = default_item.model_copy(update=patch_data)

            # Set values
            if new_item.scheduler_id is None:
                new_item.scheduler_id = s.scheduler_id
        except Exception as exc:
            # TODO: better exception handling
            self.logger.exception(exc)
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            ) from exc

        try:
            s.push_item_to_queue(new_item)
        except ValueError as exc_value:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                detail="malformed item",
            ) from exc_value
        except queues.QueueFullError as exc_full:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_429_TOO_MANY_REQUESTS,
                detail="queue is full",
            ) from exc_full
        except queues.errors.NotAllowedError as exc_not_allowed:
            raise fastapi.HTTPException(
                headers={"Retry-After": "60"},
                status_code=fastapi.status.HTTP_409_CONFLICT,
                detail=str(exc_not_allowed),
            ) from exc_not_allowed

        return new_item
