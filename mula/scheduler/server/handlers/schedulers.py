import datetime
from typing import Any

import fastapi
import structlog
from fastapi import status

from scheduler import context, models, schedulers, storage
from scheduler.server import serializers, utils
from scheduler.server.errors import BadRequestError, NotFoundError


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
            path="/schedulers/{scheduler_id}",
            endpoint=self.push,
            methods=["POST"],
            response_model=models.Task,
            status_code=status.HTTP_200_OK,
            description="Push a task to a scheduler",
        )

    def list(self, request: fastapi.Request) -> Any:
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
        limit: int = 1,
        filters: storage.filters.FilterRequest | None = None,
    ) -> Any:
        results, count = self.ctx.datastores.pq_store.pop(offset=offset, limit=limit, filters=filters)

        # TODO: see if we can batch this
        # Update status for popped items
        for item in results:
            self.ctx.datastores.pq_store.update_item(item)

        return utils.paginate(request, results, count, offset, limit)

    def push(self, scheduler_id: str, item: serializers.Task) -> Any:
        s = self.schedulers.get(scheduler_id)
        if s is None:
            raise NotFoundError(f"Scheduler {scheduler_id} not found")

        # Load default values
        new_item = models.Task(**item.model_dump(exclude_unset=True))

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
