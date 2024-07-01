from typing import Any

import fastapi
import prometheus_client
import structlog
from fastapi import status

from scheduler import context, models, queues, schedulers, storage, version


class HealthAPI:
    def __init__(self, api: fastapi.FastAPI, ctx: context.AppContext) -> None:
        self.logger: structlog.BoundLogger = structlog.getLogger(__name__)
        self.api = api
        self.ctx = ctx

        self.api.add_api_route(
            path="/health",
            endpoint=self.health,
            methods=["GET"],
            response_model=models.ServiceHealth,
            status_code=status.HTTP_200_OK,
            description="Health check endpoint",
        )

    def health(self, externals: bool = False) -> Any:
        response = models.ServiceHealth(
            service="scheduler",
            healthy=True,
            version=version.__version__,
        )

        if externals:
            for service in self.ctx.services.__dict__.values():
                response.externals[service.name] = service.is_healthy()

        return response
