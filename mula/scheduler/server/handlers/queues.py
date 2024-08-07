from typing import Any

import fastapi
import structlog
from fastapi import status

from scheduler import context, models, queues, schedulers, storage
from scheduler.server import serializers


class QueueAPI:
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
            response_model=models.PrioritizedItem | None,
            status_code=status.HTTP_200_OK,
            description="Pop an item from a queue",
        )

        self.api.add_api_route(
            path="/queues/{queue_id}/push",
            endpoint=self.push,
            methods=["POST"],
            response_model=models.PrioritizedItem | None,
            status_code=status.HTTP_201_CREATED,
            description="Push an item to a queue",
        )

    def list(self) -> Any:
        return [models.Queue(**s.queue.dict(include_pq=False)) for s in self.schedulers.copy().values()]

    def get(self, queue_id: str) -> Any:
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

    def pop(self, queue_id: str, filters: storage.filters.FilterRequest | None = None) -> Any:
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

        return models.PrioritizedItem(**p_item.model_dump())

    def push(self, queue_id: str, item: serializers.PrioritizedItem) -> Any:
        s = self.schedulers.get(queue_id)
        if s is None:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail="queue not found",
            )

        try:
            # Load default values
            p_item = models.PrioritizedItem()

            # Set values
            if p_item.scheduler_id is None:
                p_item.scheduler_id = s.scheduler_id

            p_item.priority = item.priority

            if s.queue.item_type == models.BoefjeTask:
                p_item.data = models.BoefjeTask(**item.data).dict()
                p_item.id = p_item.data["id"]
            elif s.queue.item_type == models.NormalizerTask:
                p_item.data = models.NormalizerTask(**item.data).dict()
                p_item.id = p_item.data["id"]
            else:
                p_item.data = item.data
        except Exception as exc:
            self.logger.exception(exc)
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            ) from exc

        try:
            s.push_item_to_queue(p_item)
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

        return p_item
