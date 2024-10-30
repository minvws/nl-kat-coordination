from typing import Any

import fastapi
import structlog
from fastapi import status

from scheduler import context, models, queues, schedulers, storage
from scheduler.server import serializers
from scheduler.server.errors import BadRequestError, ConflictError, NotFoundError, TooManyRequestsError


class QueueAPI:
    def __init__(self, api: fastapi.FastAPI, ctx: context.AppContext, s: dict[str, schedulers.Scheduler]) -> None:
        self.logger: structlog.BoundLogger = structlog.getLogger(__name__)
        self.api: fastapi.FastAPI = api
        self.ctx: context.AppContext = ctx
        self.schedulers: dict[str, schedulers.Scheduler] = s

        self.api.add_api_route(
            path="/queues",
            endpoint=self.list,
            methods=["GET"],
            response_model=list[models.Queue],
            response_model_exclude_unset=True,
            status_code=status.HTTP_200_OK,
            description="List all queues",
        )

        self.api.add_api_route(
            path="/queues/{queue_id}",
            endpoint=self.get,
            methods=["GET"],
            response_model=models.Queue,
            status_code=status.HTTP_200_OK,
            description="Get a queue",
        )

        self.api.add_api_route(
            path="/queues/{queue_id}/pop",
            endpoint=self.pop,
            methods=["POST"],
            response_model=models.Task | None,
            status_code=status.HTTP_200_OK,
            description="Pop an item from a queue",
        )

        self.api.add_api_route(
            path="/queues/{queue_id}/push",
            endpoint=self.push,
            methods=["POST"],
            response_model=models.Task | None,
            status_code=status.HTTP_201_CREATED,
            description="Push an item to a queue",
        )

    def list(self) -> Any:
        return [models.Queue(**s.queue.dict(include_pq=False)) for s in self.schedulers.copy().values()]

    def get(self, queue_id: str) -> Any:
        s = self.schedulers.get(queue_id)
        if s is None:
            raise NotFoundError(f"queue not found, by queue_id: {queue_id}")

        return models.Queue(**s.queue.dict())

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
