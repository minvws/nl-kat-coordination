import logging
import queue as _queue
from typing import Any, Dict, List, Union

import fastapi
import scheduler
import uvicorn
from scheduler import context, models, queues, schedulers

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
        self.queues: Dict[str, queues.PriorityQueue] = {k: s.queue for k, s in self.schedulers.items()}

        self.api = fastapi.FastAPI()

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
            methods=["GET"],
            response_model=models.QueuePrioritizedItem,
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
            version=scheduler.__version__,
        )

        for service in self.ctx.services.__dict__.values():
            response.externals[service.name] = service.is_healthy()

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

        # Update the patched attributes
        for attr, value in patch_data.items():
            try:
                setattr(s, attr, value)
            except AttributeError as exc:
                raise fastapi.HTTPException(
                    status_code=400,
                    detail="attribute not found",
                ) from exc

        return updated_scheduler

    def list_tasks(
        self,
        request: fastapi.Request,
        scheduler_id: Union[str, None] = None,
        status: Union[str, None] = None,
        offset: int = 0,
        limit: int = 10,
    ) -> Any:
        try:
            results, count = self.ctx.datastore.get_tasks(
                scheduler_id=scheduler_id,
                status=status,
                offset=offset,
                limit=limit,
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
            task = self.ctx.datastore.get_task_by_id(task_id)
        except ValueError as exc:
            raise fastapi.HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc
        except Exception as exc:
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

    def patch_task(self, task_id: str, item: models.Task) -> Any:
        try:
            task_db = self.ctx.datastore.get_task_by_id(task_id)
        except ValueError as exc:
            raise fastapi.HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            raise fastapi.HTTPException(
                status_code=500,
                detail="failed to get task",
            ) from exc

        if task_db is None:
            raise fastapi.HTTPException(
                status_code=404,
                detail="task not found",
            )

        patch_data = item.dict(exclude_unset=True)
        if len(patch_data) == 0:
            raise fastapi.HTTPException(
                status_code=400,
                detail="no data to patch",
            )

        # Update the patched attributes
        for attr, value in patch_data.items():
            try:
                setattr(task_db, attr, value)
            except AttributeError as exc:
                raise fastapi.HTTPException(
                    status_code=400,
                    detail="attribute not found",
                ) from exc

        # update task in database
        try:
            updated_task = self.ctx.datastore.update_task(task_db)
        except Exception as exc:
            raise fastapi.HTTPException(
                status_code=500,
                detail="failed to update task",
            ) from exc

        return updated_task

    def get_queues(self) -> Any:
        return [models.Queue(**q.dict()) for q in self.queues.values()]

    def get_queue(self, queue_id: str) -> Any:
        q = self.queues.get(queue_id)
        if q is None:
            raise fastapi.HTTPException(
                status_code=404,
                detail="queue not found",
            )

        return models.Queue(**q.dict())

    def pop_queue(self, queue_id: str) -> Any:
        s = self.schedulers.get(queue_id)
        if s is None:
            raise fastapi.HTTPException(
                status_code=404,
                detail="queue not found",
            )

        try:
            p_item = s.pop_item_from_queue()
        except _queue.Empty as exc_empty:
            raise fastapi.HTTPException(
                status_code=400,
                detail="queue is empty",
            ) from exc_empty

        return models.QueuePrioritizedItem(**p_item.dict())

    def push_queue(self, queue_id: str, item: models.QueuePrioritizedItem) -> Any:
        s = self.schedulers.get(queue_id)
        if s is None:
            raise fastapi.HTTPException(
                status_code=404,
                detail="queue not found",
            )

        try:
            p_item = queues.PrioritizedItem(**item.dict())
            if s.queue.item_type == models.BoefjeTask:
                p_item.item = models.BoefjeTask(**p_item.item)
            elif s.queue.item_type == models.NormalizerTask:
                p_item.item = models.NormalizerTask(**p_item.item)
        except Exception as exc:
            raise fastapi.HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        try:
            s.push_item_to_queue(p_item)
        except _queue.Full as exc_full:
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

        return models.QueuePrioritizedItem(**p_item.dict())

    def run(self) -> None:
        uvicorn.run(
            self.api,
            host=self.ctx.config.api_host,
            port=self.ctx.config.api_port,
            log_config=None,
        )
