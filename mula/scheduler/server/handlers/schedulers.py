from typing import Any

import fastapi
import structlog
from fastapi import status

from scheduler import context, models, schedulers
from scheduler.server.errors import BadRequestError, NotFoundError
from scheduler.server.models import Scheduler


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
            response_model=list[Scheduler],
            status_code=status.HTTP_200_OK,
            description="List all schedulers",
        )

        self.api.add_api_route(
            path="/schedulers/{scheduler_id}",
            endpoint=self.get,
            methods=["GET"],
            response_model=Scheduler,
            status_code=status.HTTP_200_OK,
            description="Get a scheduler",
        )

        self.api.add_api_route(
            path="/schedulers/{scheduler_id}",
            endpoint=self.patch,
            methods=["PATCH"],
            response_model=Scheduler,
            status_code=status.HTTP_200_OK,
            description="Update a scheduler",
        )

    def list(self) -> Any:
        return [Scheduler(**s.dict()) for s in self.schedulers.values()]

    def get(self, scheduler_id: str) -> Any:
        s = self.schedulers.get(scheduler_id)
        if s is None:
            raise NotFoundError(f"Scheduler {scheduler_id} not found")

        return Scheduler(**s.dict())

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

        return Scheduler(**updated_scheduler.dict())
