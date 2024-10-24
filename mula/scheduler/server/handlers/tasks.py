import datetime
import uuid
from typing import Any

import fastapi
import structlog
from fastapi import status

from scheduler import context, models, storage
from scheduler.server import serializers, utils
from scheduler.server.errors import BadRequestError, NotFoundError


class TaskAPI:
    def __init__(self, api: fastapi.FastAPI, ctx: context.AppContext) -> None:
        self.logger: structlog.BoundLogger = structlog.getLogger(__name__)
        self.api = api
        self.ctx = ctx

        self.api.add_api_route(
            path="/tasks",
            endpoint=self.list,
            methods=["GET", "POST"],
            response_model=utils.PaginatedResponse,
            status_code=status.HTTP_200_OK,
            description="List all tasks",
        )

        self.api.add_api_route(
            path="/tasks/stats",
            endpoint=self.stats,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
            description="Get task status counts for all schedulers in last 24 hours",
        )

        self.api.add_api_route(
            path="/tasks/stats/{scheduler_id}",
            endpoint=self.stats,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
            description="Get task status counts for a scheduler in last 24 hours",
        )

        self.api.add_api_route(
            path="/tasks/{task_id}",
            endpoint=self.get,
            methods=["GET"],
            response_model=models.Task,
            status_code=status.HTTP_200_OK,
            description="Get a task",
        )

        self.api.add_api_route(
            path="/tasks/{task_id}",
            endpoint=self.patch,
            methods=["PATCH"],
            response_model=models.Task,
            response_model_exclude_unset=True,
            status_code=status.HTTP_200_OK,
            description="Update a task",
        )

    def list(
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
            raise BadRequestError("min_created_at must be less than max_created_at")

        # FIXME: deprecated; backwards compatibility for rocky that uses the
        # input_ooi and plugin_id parameters.
        f_req = filters or storage.filters.FilterRequest(filters={})
        if input_ooi is not None:
            if task_type == "boefje":
                f_ooi = {
                    "and": [storage.filters.Filter(column="data", field="input_ooi", operator="eq", value=input_ooi)]
                }
            elif task_type == "normalizer":
                f_ooi = {
                    "and": [
                        storage.filters.Filter(
                            column="data", field="raw_data__boefje_meta__input_ooi", operator="eq", value=input_ooi
                        )
                    ]
                }
            else:
                f_ooi = {
                    "or": [
                        storage.filters.Filter(column="data", field="input_ooi", operator="eq", value=input_ooi),
                        storage.filters.Filter(
                            column="data", field="raw_data__boefje_meta__input_ooi", operator="eq", value=input_ooi
                        ),
                    ]
                }

            f_req.filters.update(f_ooi)  # type: ignore

        if plugin_id is not None:
            if task_type == "boefje":
                f_plugin = {
                    "and": [storage.filters.Filter(column="data", field="boefje__id", operator="eq", value=plugin_id)]
                }
            elif task_type == "normalizer":
                f_plugin = {
                    "and": [
                        storage.filters.Filter(column="data", field="normalizer__id", operator="eq", value=plugin_id)
                    ]
                }
            else:
                f_plugin = {
                    "or": [
                        storage.filters.Filter(column="data", field="boefje__id", operator="eq", value=plugin_id),
                        storage.filters.Filter(column="data", field="normalizer__id", operator="eq", value=plugin_id),
                    ]
                }

            f_req.filters.update(f_plugin)  # type: ignore

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

        return utils.paginate(request, results, count, offset, limit)

    def get(self, task_id: uuid.UUID) -> Any:
        task = self.ctx.datastores.task_store.get_task(task_id)
        if task is None:
            raise NotFoundError(f"task not found, by task_id: {task_id}")
        return task

    def patch(self, task_id: uuid.UUID, item: serializers.Task) -> Any:
        task_db = self.ctx.datastores.task_store.get_task(task_id)

        if task_db is None:
            raise NotFoundError(f"task not found, by task_id: {task_id}")

        patch_data = item.model_dump(exclude_unset=True)
        if len(patch_data) == 0:
            raise BadRequestError("no data to patch")

        # Update task
        updated_task = task_db.model_copy(update=patch_data)

        self.ctx.datastores.task_store.update_task(updated_task)

        return updated_task

    def stats(self, scheduler_id: str | None = None) -> dict[str, dict[str, int]] | None:
        return self.ctx.datastores.task_store.get_status_count_per_hour(scheduler_id)
