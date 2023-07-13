import datetime
import logging
from typing import Any, Dict, List, Optional

import fastapi
import prometheus_client
import uvicorn
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from scheduler import context, models, queues, schedulers, version
from scheduler.config import settings

from .pagination import PaginatedResponse, paginate


class Server:
    """Server that exposes API endpoints for the scheduler."""

    def __init__(
        self,
        ctx: context.AppContext,
        s: Dict[str, schedulers.Scheduler],
    ):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.ctx: context.AppContext = ctx
        self.schedulers: Dict[str, schedulers.Scheduler] = s
        self.config: settings.Settings = settings.Settings()

        self.api = fastapi.FastAPI()

        # Set up OpenTelemetry instrumentation
        if self.config.span_export_grpc_endpoint is not None:
            self.logger.info(
                "Setting up instrumentation with span exporter endpoint [%s]", self.config.span_export_grpc_endpoint
            )

            FastAPIInstrumentor.instrument_app(self.api)
            Psycopg2Instrumentor().instrument()
            RequestsInstrumentor().instrument()

            resource = Resource(attributes={SERVICE_NAME: "mula"})
            provider = TracerProvider(resource=resource)
            processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=self.config.span_export_grpc_endpoint))
            provider.add_span_processor(processor)
            trace.set_tracer_provider(provider)

            self.logger.debug("Finished setting up instrumentation")

        self.api.add_api_route(
            path="/",
            endpoint=self.root,
            methods=["GET"],
            status_code=200,
        )

        self.api.add_api_route(
            path="/health",
            endpoint=self.health,
            methods=["GET"],
            response_model=models.ServiceHealth,
            status_code=200,
        )

        self.api.add_api_route(
            path="/metrics",
            endpoint=self.metrics,
            methods=["GET"],
            status_code=200,
        )

        self.api.add_api_route(
            path="/schedulers",
            endpoint=self.get_schedulers,
            methods=["GET"],
            response_model=List[models.Scheduler],
            status_code=200,
        )

        self.api.add_api_route(
            path="/schedulers/{scheduler_id}",
            endpoint=self.get_scheduler,
            methods=["GET"],
            response_model=models.Scheduler,
            status_code=200,
        )

        self.api.add_api_route(
            path="/schedulers/{scheduler_id}",
            endpoint=self.patch_scheduler,
            methods=["PATCH"],
            response_model=models.Scheduler,
            status_code=200,
        )

        self.api.add_api_route(
            path="/schedulers/{scheduler_id}/tasks",
            endpoint=self.list_tasks,
            methods=["GET"],
            response_model=PaginatedResponse,
            status_code=200,
        )

        self.api.add_api_route(
            path="/tasks",
            endpoint=self.list_tasks,
            methods=["GET"],
            response_model=PaginatedResponse,
            status_code=200,
        )

        self.api.add_api_route(
            path="/tasks/{task_id}",
            endpoint=self.get_task,
            methods=["GET"],
            response_model=models.Task,
            status_code=200,
        )

        self.api.add_api_route(
            path="/tasks/{task_id}",
            endpoint=self.patch_task,
            methods=["PATCH"],
            response_model=models.Task,
            status_code=200,
        )

        self.api.add_api_route(
            path="/queues",
            endpoint=self.get_queues,
            methods=["GET"],
            response_model=List[models.Queue],
            response_model_exclude_unset=True,
            status_code=200,
        )

        self.api.add_api_route(
            path="/queues/{queue_id}",
            endpoint=self.get_queue,
            methods=["GET"],
            response_model=models.Queue,
            status_code=200,
        )

        self.api.add_api_route(
            path="/queues/{queue_id}/pop",
            endpoint=self.pop_queue,
            methods=["POST"],
            response_model=Optional[models.PrioritizedItem],
            status_code=200,
        )

        self.api.add_api_route(
            path="/queues/{queue_id}/push",
            endpoint=self.push_queue,
            methods=["POST"],
            status_code=201,
        )

    def root(self) -> Any:
        return None

    def health(self) -> Any:
        response = models.ServiceHealth(
            service="scheduler",
            healthy=True,
            version=version.__version__,
        )

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
                status_code=404,
                detail="scheduler not found",
            )

        return models.Scheduler(**s.dict())

    def patch_scheduler(self, scheduler_id: str, item: models.Scheduler) -> Any:
        s = self.schedulers.get(scheduler_id)
        if s is None:
            raise fastapi.HTTPException(
                status_code=404,
                detail="scheduler not found",
            )

        stored_scheduler_model = models.Scheduler(**s.dict())
        patch_data = item.dict(exclude_unset=True)
        if len(patch_data) == 0:
            raise fastapi.HTTPException(
                status_code=400,
                detail="no data to patch",
            )

        updated_scheduler = stored_scheduler_model.copy(update=patch_data)

        # We update the patched attributes, since the schedulers are kept
        # in memory.
        for attr, value in patch_data.items():
            try:
                setattr(s, attr, value)
            except AttributeError as exc:
                raise fastapi.HTTPException(
                    status_code=400,
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
        scheduler_id: Optional[str] = None,
        task_type: Optional[str] = None,
        status: Optional[str] = None,
        offset: int = 0,
        limit: int = 10,
        min_created_at: Optional[datetime.datetime] = None,
        max_created_at: Optional[datetime.datetime] = None,
        input_ooi: Optional[str] = None,
        plugin_id: Optional[str] = None,
    ) -> Any:
        try:
            if (min_created_at is not None and max_created_at is not None) and min_created_at > max_created_at:
                raise ValueError("min_date must be less than max_date")

            results, count = self.ctx.task_store.api_list_tasks(
                scheduler_id=scheduler_id,
                task_type=task_type,
                status=status,
                offset=offset,
                limit=limit,
                min_created_at=min_created_at,
                max_created_at=max_created_at,
                input_ooi=input_ooi,
                plugin_id=plugin_id,
            )
        except ValueError as exc:
            raise fastapi.HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            self.logger.exception(exc)
            raise fastapi.HTTPException(
                status_code=500,
                detail="failed to get tasks",
            ) from exc

        return paginate(request, results, count=count, offset=offset, limit=limit)

    def get_task(self, task_id: str) -> Any:
        try:
            task = self.ctx.task_store.get_task_by_id(task_id)
        except ValueError as exc:
            raise fastapi.HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            self.logger.exception(exc)
            raise fastapi.HTTPException(
                status_code=500,
                detail="failed to get task",
            ) from exc

        if task is None:
            raise fastapi.HTTPException(
                status_code=404,
                detail="task not found",
            )

        return models.Task(**task.dict())

    def patch_task(self, task_id: str, item: Dict) -> Any:
        if len(item) == 0:
            raise fastapi.HTTPException(
                status_code=400,
                detail="no data to patch",
            )

        try:
            task_db = self.ctx.task_store.get_task_by_id(task_id)
        except Exception as exc:
            raise fastapi.HTTPException(
                status_code=400,
                detail=f"failed to get task [exception: {exc}]",
            ) from exc

        if task_db is None:
            raise fastapi.HTTPException(
                status_code=404,
                detail="task not found",
            )

        updated_task = task_db.copy(update=item)

        # Update task in database
        try:
            self.ctx.task_store.update_task(updated_task)
        except Exception as exc:
            self.logger.error(exc)
            raise fastapi.HTTPException(
                status_code=500,
                detail="failed to update task",
            ) from exc

        return updated_task

    def get_queues(self) -> Any:
        return [models.Queue(**s.queue.dict(include_pq=False)) for s in self.schedulers.copy().values()]

    def get_queue(self, queue_id: str) -> Any:
        s = self.schedulers.get(queue_id)
        if s is None:
            raise fastapi.HTTPException(
                status_code=404,
                detail="scheduler not found, by queue_id",
            )

        q = s.queue
        if q is None:
            raise fastapi.HTTPException(
                status_code=404,
                detail="queue not found",
            )

        return models.Queue(**q.dict())

    def pop_queue(self, queue_id: str, filters: Optional[List[models.Filter]] = None) -> Any:
        s = self.schedulers.get(queue_id)
        if s is None:
            raise fastapi.HTTPException(
                status_code=404,
                detail="queue not found",
            )

        try:
            p_item = s.pop_item_from_queue(filters)
        except queues.QueueEmptyError:
            return None

        if p_item is None:
            raise fastapi.HTTPException(
                status_code=404,
                detail="could not pop item from queue, check your filters",
            )

        return models.PrioritizedItem(**p_item.dict())

    def push_queue(self, queue_id: str, item: models.PrioritizedItem) -> Any:
        s = self.schedulers.get(queue_id)
        if s is None:
            raise fastapi.HTTPException(
                status_code=404,
                detail="queue not found",
            )

        try:
            p_item = models.PrioritizedItem(**item.dict())
            if p_item.scheduler_id is None:
                p_item.scheduler_id = s.scheduler_id

            if s.queue.item_type == models.BoefjeTask:
                p_item.data = models.BoefjeTask(**p_item.data).dict()
            elif s.queue.item_type == models.NormalizerTask:
                p_item.data = models.NormalizerTask(**p_item.data).dict()
        except Exception as exc:
            raise fastapi.HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        try:
            s.push_item_to_queue(p_item)
        except queues.QueueFullError as exc_full:
            raise fastapi.HTTPException(
                status_code=400,
                detail="queue is full",
            ) from exc_full
        except ValueError as exc_value:
            raise fastapi.HTTPException(
                status_code=400,
                detail="invalid item",
            ) from exc_value
        except queues.errors.NotAllowedError as exc_not_allowed:
            raise fastapi.HTTPException(
                status_code=400,
                detail="not allowed",
            ) from exc_not_allowed

        return models.PrioritizedItem(**p_item.dict())

    def run(self) -> None:
        uvicorn.run(
            self.api,
            host=self.ctx.config.api_host,
            port=self.ctx.config.api_port,
            log_config=None,
        )
