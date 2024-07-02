import datetime
import uuid
from typing import Any

import fastapi
import structlog
from fastapi import status

from scheduler import context, models, storage

from .. import serializers, utils


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
        if (
            min_created_at is not None and max_created_at is not None
        ) and min_created_at > max_created_at:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                detail="min_date must be less than max_date",
            )

        # FIXME: deprecated; backwards compatibility for rocky that uses the
        # input_ooi and plugin_id parameters.
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
                f_plugin = storage.filters.Filter(
                    column="p_item",
                    field="data__normalizer__id",
                    operator="eq",
                    value=plugin_id,
                )
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

        return utils.paginate(request, results, count, offset, limit)

    def get(self, task_id: uuid.UUID) -> Any:
        try:
            task = self.ctx.datastores.task_store.get_task(task_id)
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

        return task

    # NOTE: serializers.Task instead of models.Task is needed for patch
    # endpoints # to allow for partial updates.
    def patch(self, task_id: uuid.UUID, item: serializers.Task) -> Any:
        try:
            task_db = self.ctx.datastores.task_store.get_task(task_id)
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
        except storage.errors.StorageError as exc:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"error occurred while accessing the database [exception: {exc}]",
            ) from exc
        except Exception as exc:
            self.logger.exception(exc)
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="failed to update task",
            ) from exc

        return updated_task

    def stats(
        self, scheduler_id: str | None = None
    ) -> dict[str, dict[str, int]] | None:
        try:
            stats = self.ctx.datastores.task_store.get_status_count_per_hour(
                scheduler_id
            )
        except Exception as exc:
            self.logger.exception(exc)
            self.logger.exception(exc)
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="failed to get task stats",
            ) from exc

        return stats
