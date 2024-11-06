from typing import Any

import fastapi
import structlog
from fastapi import status

from scheduler import context, models, schedulers
from scheduler.server.errors import BadRequestError, NotFoundError


class SchedulerAPI:
    def __init__(self, api: fastapi.FastAPI, ctx: context.AppContext, s: dict[str, schedulers.Scheduler]) -> None:
        self.logger: structlog.BoundLogger = structlog.getLogger(__name__)
        self.api: fastapi.FastAPI = api
        self.ctx: context.AppContext = ctx
        self.schedulers: dict[str, schedulers.Scheduler] = s

        self.api.add_api_route(
            path="/schedulers",
            endpoint=self.list,
            methods=["GET"],
            response_model=list[models.Scheduler],
            status_code=status.HTTP_200_OK,
            description="List all schedulers",
        )

        self.api.add_api_route(
            path="/schedulers/{scheduler_id}",
            endpoint=self.get,
            methods=["GET"],
            response_model=models.Scheduler,
            status_code=status.HTTP_200_OK,
            description="Get a scheduler",
        )

        self.api.add_api_route(
            path="/schedulers/{scheduler_id}",
            endpoint=self.patch,
            methods=["PATCH"],
            response_model=models.Scheduler,
            status_code=status.HTTP_200_OK,
            description="Update a scheduler",
        )

    def list(self) -> Any:
        return [models.Scheduler(**s.dict()) for s in self.schedulers.values()]

    def get(self, scheduler_id: str) -> Any:
        s = self.schedulers.get(scheduler_id)
        if s is None:
            raise NotFoundError(f"Scheduler {scheduler_id} not found")

        return models.Scheduler(**s.dict())

    def patch(self, scheduler_id: str, item: models.Scheduler) -> Any:
        s = self.schedulers.get(scheduler_id)
        if s is None:
            raise NotFoundError(f"Scheduler {scheduler_id} not found")

        stored_scheduler_model = models.Scheduler(**s.dict())
        patch_data = item.model_dump(exclude_unset=True)
        if len(patch_data) == 0:
            raise BadRequestError("no data to patch")

        updated_scheduler = stored_scheduler_model.model_copy(update=patch_data)

        # We update the patched attributes, since the schedulers are kept
        # in memory.
        for attr, value in patch_data.items():
            setattr(s, attr, value)

        # Enable or disable the scheduler if needed.
        if updated_scheduler.enabled:
            s.enable()
        elif not updated_scheduler.enabled:
            s.disable()

        return updated_scheduler

    # FIXME
    def pop(self, queue_id: str, filters: storage.filters.FilterRequest | None = None) -> Any:
        s = self.schedulers.get(queue_id)
        if s is None:
            raise NotFoundError(f"queue not found, by queue_id: {queue_id}")

        try:
            item = s.pop_item_from_queue(filters)
        except queues.QueueEmptyError:
            return None

        if item is None:
            raise NotFoundError("could not pop item from queue, check your filters")

        return models.Task(**item.model_dump())

    def push(self, queue_id: str, item_in: serializers.Task) -> Any:
        s = self.schedulers.get(queue_id)
        if s is None:
            raise NotFoundError(f"queue not found, by queue_id: {queue_id}")

        # Load default values
        new_item = models.Task(**item_in.model_dump(exclude_unset=True))

        # Set values
        if new_item.scheduler_id is None:
            new_item.scheduler_id = s.scheduler_id

        try:
            pushed_item = s.push_item_to_queue(new_item)
        except ValueError:
            raise BadRequestError("malformed item")
        except queues.QueueFullError:
            raise TooManyRequestsError("queue is full")
        except queues.errors.NotAllowedError:
            raise ConflictError("queue is not allowed to push items")

        return pushed_item
