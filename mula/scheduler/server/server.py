import datetime
import uuid
from typing import Any

import fastapi
import structlog
import uvicorn
from fastapi import status

from scheduler import context, models, queues, schedulers, storage, version
from scheduler.config import settings
from scheduler.models.errors import ValidationError

from . import handlers, serializers


class Server:
    """Server that exposes API endpoints for the scheduler.

    Attributes:
        logger: A structlog.BoundLogger object used for logging.
        ctx: A context.AppContext object used for sharing data between modules.
        schedulers: A dict containing all the schedulers.
        config: A settings.Settings object containing the configuration settings.
        api: A fastapi.FastAPI object used for exposing API endpoints.
    """

    def __init__(
        self,
        ctx: context.AppContext,
        schedulers: dict[str, schedulers.Scheduler],
    ):
        """Initializer of the Server class.

        Args:
            ctx: A context.AppContext object used for sharing data between modules.
            s: A dict containing all the schedulers.
        """

        self.logger: structlog.BoundLogger = structlog.getLogger(__name__)
        self.ctx: context.AppContext = ctx
        self.api: fastapi.FastAPI = fastapi.FastAPI(
            title="Scheduler",
            version=version.VERSION,
            description="Scheduler API",
        )
        self.scheduler: dict[str, schedulers.Scheduler] = schedulers

        # Set up API endpoints
        handlers.SchedulerAPI(self.api, self.ctx, schedulers)
        handlers.ScheduleAPI(self.api, self.ctx)
        handlers.TaskAPI(self.api, self.ctx)
        handlers.MetricsAPI(self.api, self.ctx)
        handlers.HealthAPI(self.api, self.ctx)
        handlers.RootAPI(self.api, self.ctx)

    def run(self) -> None:
        uvicorn.run(
            self.api,
            host=str(self.ctx.config.api_host),
            port=self.ctx.config.api_port,
            log_config=None,
        )
