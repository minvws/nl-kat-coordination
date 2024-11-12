import datetime
from typing import Any

import fastapi
import structlog
from fastapi import status

from scheduler import context, models, schedulers, storage
from scheduler.server import serializers, utils
from scheduler.server.errors import BadRequestError, NotFoundError


class SchedulerAPI:
    def __init__(self, api: fastapi.FastAPI, ctx: context.AppContext):
        self.logger: structlog.BoundLogger = structlog.getLogger(__name__)
        self.api: fastapi.FastAPI = api
        self.ctx: context.AppContext = ctx

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

    def list(
        self,
        request: fastapi.Request,
        scheduler_id: str | None = None,
        scheduler_type: str | None = None,
        organisation: str | None = None,
        offset: int = 0,
        limit: int = 10,
        min_created_at: datetime.datetime | None = None,
        max_created_at: datetime.datetime | None = None,
    ) -> Any:
        if (min_created_at is not None and max_created_at is not None) and min_created_at > max_created_at:
            raise BadRequestError("min_created_at must be less than max_created_at")

        results, count = self.ctx.datastores.scheduler_store.get_schedulers(
            scheduler_id=scheduler_id,
            scheduler_type=scheduler_type,
            organisation=organisation,
            offset=offset,
            limit=limit,
            min_created_at=min_created_at,
            max_created_at=max_created_at,
        )

        return utils.paginate(request, results, count, offset, limit)

    def create(self, item: serializers.Scheduler) -> Any:
        pass

    def get(self, scheduler_id: str) -> Any:
        scheduler = self.ctx.datastores.scheduler_store.get_scheduler(scheduler_id)
        if scheduler is None:
            raise NotFoundError(f"Scheduler {scheduler_id} not found")

        return scheduler

    def patch(self, scheduler_id: str, item: models.Scheduler) -> Any:
        scheduler_db = self.ctx.datastores.scheduler_store.get_scheduler(scheduler_id)
        if scheduler_db is None:
            raise NotFoundError(f"Scheduler {scheduler_id} not found")

        patch_data = scheduler_db.model_dump(exclude_unset=True)
        if len(patch_data) == 0:
            raise BadRequestError("no data to patch")

        updated_scheduler = scheduler_db.model_copy(update=patch_data)

        # TODO: what to do with the running scheduler?

        # TODO: enable or disable the scheduler if needed.

        # Update the scheduler in database
        self.ctx.datastores.scheduler_store.update_scheduler(updated_scheduler)

        return updated_scheduler

    def pop(
        self,
        request: fastapi.Request,
        offset: int = 0,
        limit: int = 100,
        filters: storage.filters.FilterRequest | None = None,
    ) -> Any:
        results, count = self.ctx.datastores.pq_store.pop(offset=offset, limit=limit, filters=filters)

        # TODO: see if we can batch this
        # Update status for popped items
        for item in results:
            self.ctx.datastores.pq_store.update_item(item)

        return utils.paginate(request, results, count, offset, limit)

    # FIXME
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
