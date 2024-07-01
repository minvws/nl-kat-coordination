from typing import Any

import fastapi
import structlog

from scheduler import context, models

from .. import serializers, utils


class ScheduleAPI:

    def __init__(self, api: fastapi.FastAPI, ctx: context.AppContext) -> None:
        self.logger: structlog.BoundLogger = structlog.getLogger(__name__)
        self.api = api
        self.ctx = ctx

        self.api.add_api_route(
            path="/schedules",
            endpoint=self.list,
            methods=["GET", "POST"],
            response_model=utils.PaginatedResponse,
            status_code=200,
            description="List all schedules",
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

    def list(self) -> Any:
        return None

    def get(self, schedule_id: str) -> Any:
        return None

    def create(self, schedule: models.Schedule) -> Any:
        return None

    def patch(self, schedule_id: str, schedule: models.Schedule) -> Any:
        return None

    def delete(self, schedule_id: str) -> Any:
        return None
