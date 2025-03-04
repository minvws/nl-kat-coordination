from re import X
from typing import Any

import fastapi
import structlog
from fastapi import status

from scheduler import context, version
from scheduler.server import serializers


class HealthAPI:
    def __init__(self, api: fastapi.FastAPI, ctx: context.AppContext) -> None:
        self.logger: structlog.BoundLogger = structlog.getLogger(__name__)
        self.api = api
        self.ctx = ctx

        self.api.add_api_route(
            path="/health",
            endpoint=self.health,
            methods=["GET"],
            response_model=serializers.ServiceHealth,
            status_code=status.HTTP_200_OK,
            description="Health check endpoint",
        )

    def health(self, externals: bool = False) -> serializers.ServiceHealth:
        response = serializers.ServiceHealth(service="scheduler", healthy=True, version=version.__version__)

        if externals:
            for service in self.ctx.services.__dict__.values():
                response.externals[service.name] = service.is_healthy()

        return response
