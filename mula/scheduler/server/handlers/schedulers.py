import datetime
from typing import Any

import fastapi
import structlog
from fastapi import status

from scheduler import context, models, schedulers, storage
from scheduler.schedulers.queue import NotAllowedError, QueueFullError
from scheduler.server import serializers, utils
from scheduler.server.errors import BadRequestError, ConflictError, NotFoundError, TooManyRequestsError


class SchedulerAPI:
    def __init__(self, api: fastapi.FastAPI, ctx: context.AppContext, s: dict[str, schedulers.Scheduler]):
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
            path="/schedulers/{scheduler_id}/push",
            endpoint=self.push,
            methods=["POST"],
            response_model=models.Task,
            status_code=status.HTTP_201_CREATED,
            description="Push a task to a scheduler",
        )

        self.api.add_api_route(
            path="/schedulers/{scheduler_id}/pop",
            endpoint=self.pop,
            methods=["POST"],
            response_model=utils.PaginatedResponse,
            status_code=status.HTTP_200_OK,
            description="Pop a task from a scheduler",
        )

    def list(self) -> Any:
        return [models.Scheduler(**s.dict()) for s in self.schedulers.values()]

    def get(self, scheduler_id: str) -> Any:
        s = self.schedulers.get(scheduler_id)
        if s is None:
            raise NotFoundError(f"Scheduler {scheduler_id} not found")

        return models.Scheduler(**s.dict())

    def pop(
        self,
        request: fastapi.Request,
        offset: int = 0,
        limit: int = 100,
        filters: storage.filters.FilterRequest | None = None,
    ) -> utils.PaginatedResponse:
        results, count = self.ctx.datastores.pq_store.pop(offset=offset, limit=limit, filters=filters)

        # TODO: see if we can batch this
        # Update status for popped items
        for item in results:
            item.status = models.TaskStatus.DISPATCHED
            self.ctx.datastores.pq_store.update(item.scheduler_id, item)

        return utils.paginate(request, results, count, offset, limit)

    def push(self, scheduler_id: str, item: serializers.TaskPush) -> Any:
        s = self.schedulers.get(scheduler_id)
        if s is None:
            raise NotFoundError(f"Scheduler {scheduler_id} not found")

        if item.scheduler_id is not None and item.scheduler_id != scheduler_id:
            raise BadRequestError("scheduler_id in item does not match the scheduler_id in the path")

        # Set scheduler_id if not set
        if item.scheduler_id is None:
            item.scheduler_id = scheduler_id

        # Load default values
        new_item = models.Task(**item.model_dump(exclude_unset=True))

        try:
            pushed_item = s.push_item_to_queue(new_item)
        except ValueError:
            raise BadRequestError("malformed item")
        except QueueFullError:
            raise TooManyRequestsError("queue is full")
        except NotAllowedError:
            raise ConflictError("queue is not allowed to push items")

        return pushed_item
