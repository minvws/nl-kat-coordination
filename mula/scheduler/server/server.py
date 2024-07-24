import datetime
import uuid
from typing import Any

import fastapi
import prometheus_client
import structlog
import uvicorn
from fastapi import status
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from scheduler import context, models, queues, schedulers, storage, version
from scheduler.config import settings

from . import serializers
from .pagination import PaginatedResponse, paginate


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
        s: dict[str, schedulers.Scheduler],
    ):
        """Initializer of the Server class.

        Args:
            ctx: A context.AppContext object used for sharing data between modules.
            s: A dict containing all the schedulers.
        """

        self.logger: structlog.BoundLogger = structlog.getLogger(__name__)
        self.ctx: context.AppContext = ctx
        self.schedulers: dict[str, schedulers.Scheduler] = s
        self.config: settings.Settings = settings.Settings()

        self.api = fastapi.FastAPI(title="Scheduler (Mula) API")

        # Set up OpenTelemetry instrumentation
        if self.config.host_metrics is not None:
            self.logger.info(
                "Setting up instrumentation with span exporter endpoint [%s]",
                self.config.host_metrics,
            )

            FastAPIInstrumentor.instrument_app(self.api)
            Psycopg2Instrumentor().instrument()
            HTTPXClientInstrumentor().instrument()

            resource = Resource(attributes={SERVICE_NAME: "mula"})
            provider = TracerProvider(resource=resource)
            processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=str(self.config.host_metrics)))
            provider.add_span_processor(processor)
            trace.set_tracer_provider(provider)

            self.logger.debug("Finished setting up OpenTelemetry instrumentation")

        self.api.add_api_route(
            path="/",
            endpoint=self.root,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
            description="Root endpoint",
        )

        self.api.add_api_route(
            path="/health",
            endpoint=self.health,
            methods=["GET"],
            response_model=models.ServiceHealth,
            status_code=status.HTTP_200_OK,
            description="Health check endpoint",
        )

        self.api.add_api_route(
            path="/metrics",
            endpoint=self.metrics,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
            description="OpenMetrics compliant metrics endpoint",
        )

        self.api.add_api_route(
            path="/schedulers",
            endpoint=self.get_schedulers,
            methods=["GET"],
            response_model=list[models.Scheduler],
            status_code=status.HTTP_200_OK,
            description="List all schedulers",
        )

        self.api.add_api_route(
            path="/schedulers/{scheduler_id}",
            endpoint=self.get_scheduler,
            methods=["GET"],
            response_model=models.Scheduler,
            status_code=status.HTTP_200_OK,
            description="Get a scheduler",
        )

        self.api.add_api_route(
            path="/schedulers/{scheduler_id}",
            endpoint=self.patch_scheduler,
            methods=["PATCH"],
            response_model=models.Scheduler,
            status_code=status.HTTP_200_OK,
            description="Update a scheduler",
        )

        self.api.add_api_route(
            path="/schedulers/{scheduler_id}/tasks",
            endpoint=self.list_tasks,
            methods=["GET"],
            response_model=PaginatedResponse,
            status_code=status.HTTP_200_OK,
            description="List all tasks for a scheduler",
        )

        self.api.add_api_route(
            path="/tasks",
            endpoint=self.list_tasks,
            methods=["GET", "POST"],
            response_model=PaginatedResponse,
            status_code=status.HTTP_200_OK,
            description="List all tasks",
        )

        self.api.add_api_route(
            path="/tasks/stats",
            endpoint=self.get_task_stats,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
            description="Get task status counts for all schedulers in last 24 hours",
        )

        self.api.add_api_route(
            path="/tasks/stats/{scheduler_id}",
            endpoint=self.get_task_stats,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
            description="Get task status counts for a scheduler in last 24 hours",
        )

        self.api.add_api_route(
            path="/tasks/{task_id}",
            endpoint=self.get_task,
            methods=["GET"],
            response_model=models.Task,
            status_code=status.HTTP_200_OK,
            description="Get a task",
        )

        self.api.add_api_route(
            path="/tasks/{task_id}",
            endpoint=self.patch_task,
            methods=["PATCH"],
            response_model=models.Task,
            response_model_exclude_unset=True,
            status_code=status.HTTP_200_OK,
            description="Update a task",
        )

        self.api.add_api_route(
            path="/queues",
            endpoint=self.get_queues,
            methods=["GET"],
            response_model=list[models.Queue],
            response_model_exclude_unset=True,
            status_code=status.HTTP_200_OK,
            description="List all queues",
        )

        self.api.add_api_route(
            path="/queues/{queue_id}",
            endpoint=self.get_queue,
            methods=["GET"],
            response_model=models.Queue,
            status_code=status.HTTP_200_OK,
            description="Get a queue",
        )

        self.api.add_api_route(
            path="/queues/{queue_id}/pop",
            endpoint=self.pop_queue,
            methods=["POST"],
            response_model=models.PrioritizedItem | None,
            status_code=status.HTTP_200_OK,
            description="Pop an item from a queue",
        )

        self.api.add_api_route(
            path="/queues/{queue_id}/push",
            endpoint=self.push_queue,
            methods=["POST"],
            response_model=models.PrioritizedItem | None,
            status_code=status.HTTP_201_CREATED,
            description="Push an item to a queue",
        )

    def root(self) -> Any:
        return None

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

    def metrics(self) -> Any:
        data = prometheus_client.generate_latest(self.ctx.metrics_registry)
        response = fastapi.Response(media_type="text/plain", content=data)
        return response

    def get_schedulers(self) -> Any:
        return [models.Scheduler(**s.dict()) for s in self.schedulers.values()]

    def get_scheduler(self, scheduler_id: str) -> Any:
        s = self.schedulers.get(scheduler_id)
        if s is None:
            raise fastapi.HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="scheduler not found",
            )

        return models.Scheduler(**s.dict())

    def patch_scheduler(self, scheduler_id: str, item: models.Scheduler) -> Any:
        s = self.schedulers.get(scheduler_id)
        if s is None:
            raise fastapi.HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="scheduler not found",
            )

        stored_scheduler_model = models.Scheduler(**s.dict())
        patch_data = item.model_dump(exclude_unset=True)
        if len(patch_data) == 0:
            raise fastapi.HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="no data to patch",
            )

        updated_scheduler = stored_scheduler_model.model_copy(update=patch_data)

        # We update the patched attributes, since the schedulers are kept
        # in memory.
        for attr, value in patch_data.items():
            try:
                setattr(s, attr, value)
            except AttributeError as exc:
                raise fastapi.HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="attribute not found",
                ) from exc

        # Enable or disable the scheduler if needed.
        if updated_scheduler.enabled:
            s.enable()
        elif not updated_scheduler.enabled:
            s.disable()

        return updated_scheduler

    def list_tasks(
        self,
        request: fastapi.Request,
        scheduler_id: str | None = None,
        task_type: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 10,
        min_created_at: datetime.datetime | None = None,
        max_created_at: datetime.datetime | None = None,
        input_ooi: str | None = None,  # FIXME: deprecated
        plugin_id: str | None = None,  # FIXME: deprecated
        filters: storage.filters.FilterRequest | None = None,
    ) -> Any:
        if (min_created_at is not None and max_created_at is not None) and min_created_at > max_created_at:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                detail="min_date must be less than max_date",
            )

        # FIXME: deprecated; backwards compatibility for rocky that uses the
        # input_ooi and plugin_id parameters. These filter options should be
        # defined in the filter request payload not as query parameters.
        f_req = filters or storage.filters.FilterRequest(filters={})
        if input_ooi is not None:
            if task_type == "boefje":
                f_ooi = {
                    "and": [
                        storage.filters.Filter(
                            column="p_item",
                            field="data__input_ooi",
                            operator="eq",
                            value=input_ooi,
                        )
                    ]
                }
            elif task_type == "normalizer":
                f_ooi = {
                    "and": [
                        storage.filters.Filter(
                            column="p_item",
                            field="data__raw_data__boefje_meta__input_ooi",
                            operator="eq",
                            value=input_ooi,
                        )
                    ]
                }
            else:
                f_ooi = {
                    "or": [
                        storage.filters.Filter(
                            column="p_item",
                            field="data__input_ooi",
                            operator="eq",
                            value=input_ooi,
                        ),
                        storage.filters.Filter(
                            column="p_item",
                            field="data__raw_data__boefje_meta__input_ooi",
                            operator="eq",
                            value=input_ooi,
                        ),
                    ]
                }

            f_req.filters.update(f_ooi)  # type: ignore

        # FIXME: deprecated; backwards compatibility for rocky that uses the
        # input_ooi and plugin_id parameters. These filter options should be
        # defined in the filter request payload not as query parameters.
        if plugin_id is not None:
            if task_type == "boefje":
                f_plugin = {
                    "and": [
                        storage.filters.Filter(
                            column="p_item",
                            field="data__boefje__id",
                            operator="eq",
                            value=plugin_id,
                        )
                    ]
                }
            elif task_type == "normalizer":
                f_plugin = {
                    "and": [
                        storage.filters.Filter(
                            column="p_item",
                            field="data__normalizer__id",
                            operator="eq",
                            value=plugin_id,
                        )
                    ]
                }
            else:
                f_plugin = {
                    "or": [
                        storage.filters.Filter(
                            column="p_item",
                            field="data__boefje__id",
                            operator="eq",
                            value=plugin_id,
                        ),
                        storage.filters.Filter(
                            column="p_item",
                            field="data__normalizer__id",
                            operator="eq",
                            value=plugin_id,
                        ),
                    ]
                }

            f_req.filters.update(f_plugin)  # type: ignore

        try:
            results, count = self.ctx.datastores.task_store.get_tasks(
                scheduler_id=scheduler_id,
                task_type=task_type,
                status=status,
                offset=offset,
                limit=limit,
                min_created_at=min_created_at,
                max_created_at=max_created_at,
                filters=f_req,
            )
        except storage.filters.errors.FilterError as exc:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                detail=f"invalid filter(s) [exception: {exc}]",
            ) from exc
        except storage.errors.StorageError as exc:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"error occurred while accessing the database [exception: {exc}]",
            ) from exc
        except Exception as exc:
            self.logger.exception(exc)
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="failed to get tasks",
            ) from exc

        return paginate(request, results, count=count, offset=offset, limit=limit)

    def get_task(self, task_id: uuid.UUID) -> Any:
        try:
            task = self.ctx.datastores.task_store.get_task_by_id(task_id)
        except storage.errors.StorageError as exc:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"error occurred while accessing the database [exception: {exc}]",
            ) from exc
        except Exception as exc:
            self.logger.exception(exc)
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"failed to get task [exception: {exc}]",
            ) from exc

        if task is None:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail="task not found",
            )

        return models.Task(**task.model_dump())

    # NOTE: serializers.Task instead of models.Task is needed for patch
    # endpoints # to allow for partial updates.
    def patch_task(self, task_id: uuid.UUID, item: serializers.Task) -> Any:
        try:
            task_db = self.ctx.datastores.task_store.get_task_by_id(task_id)
        except storage.errors.StorageError as exc:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"error occurred while accessing the database [exception: {exc}]",
            ) from exc
        except Exception as exc:
            self.logger.exception(exc)
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"failed to get task [exception: {exc}]",
            ) from exc

        if task_db is None:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail="task not found",
            )

        patch_data = item.model_dump(exclude_unset=True)
        if len(patch_data) == 0:
            raise fastapi.HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="no data to patch",
            )

        updated_task = task_db.model_copy(update=patch_data)

        # Update task in database
        try:
            self.ctx.datastores.task_store.update_task(updated_task)
        except Exception as exc:
            self.logger.exception(exc)
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="failed to update task",
            ) from exc

        return updated_task

    def get_task_stats(self, scheduler_id: str | None = None) -> dict[str, dict[str, int]] | None:
        try:
            stats = self.ctx.datastores.task_store.get_status_count_per_hour(scheduler_id)
        except Exception as exc:
            self.logger.exception(exc)
            self.logger.exception(exc)
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="failed to get task stats",
            ) from exc

        return stats

    def get_queues(self) -> Any:
        return [models.Queue(**s.queue.dict(include_pq=False)) for s in self.schedulers.copy().values()]

    def get_queue(self, queue_id: str) -> Any:
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

    def pop_queue(self, queue_id: str, filters: storage.filters.FilterRequest | None = None) -> Any:
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

    def push_queue(self, queue_id: str, item: serializers.PrioritizedItem) -> Any:
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

    def run(self) -> None:
        uvicorn.run(
            self.api,
            host=str(self.ctx.config.api_host),
            port=self.ctx.config.api_port,
            log_config=None,
        )
