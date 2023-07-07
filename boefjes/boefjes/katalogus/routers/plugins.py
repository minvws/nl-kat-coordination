from functools import partial
from typing import Dict, List, Literal, Optional, Union

from fastapi import APIRouter, Body, Depends, HTTPException
from requests import HTTPError
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.status import HTTP_404_NOT_FOUND

from boefjes.katalogus.dependencies.plugins import PluginService, get_plugin_service
from boefjes.katalogus.models import PluginType
from boefjes.katalogus.routers.organisations import check_organisation_exists
from boefjes.katalogus.types import LIMIT, PaginationParams, PluginsFilter

router = APIRouter(
    prefix="/organisations/{organisation_id}",
    tags=["plugins"],
    dependencies=[Depends(check_organisation_exists)],
)


def get_pagination_parameters(offset: int = 0, limit: Optional[int] = LIMIT) -> PaginationParams:
    return PaginationParams(offset=offset, limit=limit)


def get_plugins_filter(
    q: Optional[str] = None,
    plugin_type: Optional[Union[Literal["boefje"], Literal["normalizer"], Literal["bit"]]] = None,
    state: Optional[bool] = None,
) -> PluginsFilter:
    return PluginsFilter(q=q, type=plugin_type, state=state)


# check if query matches plugin id, name or description
def _plugin_matches_query(plugin: PluginType, query: str) -> bool:
    return (
        query in plugin.id
        or (plugin.name is not None and query in plugin.name)
        or (plugin.description is not None and query in plugin.description)
    )


@router.get("/plugins", response_model=List[PluginType])
def list_plugins(
    organisation_id: str,
    filter_params: PluginsFilter = Depends(get_plugins_filter),
    pagination_params: PaginationParams = Depends(get_pagination_parameters),
    plugin_service: PluginService = Depends(get_plugin_service),
) -> List[PluginType]:
    with plugin_service as p:
        plugins = p.get_all(organisation_id)

    # filter plugins by id, name or description
    if filter_params.q is not None:
        plugins = filter(
            partial(_plugin_matches_query, query=filter_params.q),
            plugins,
        )

    # filter plugins by type
    if filter_params.type is not None:
        plugins = filter(lambda plugin: plugin.type == filter_params.type, plugins)

    # filter plugins by state
    if filter_params.state is not None:
        plugins = filter(lambda x: plugin.enabled is filter_params.state, plugins)

    # paginate plugins
    plugins = list(plugins)[pagination_params.offset : pagination_params.offset + pagination_params.limit]

    return plugins


@router.get("/plugins/{plugin_id}", response_model=PluginType)
def plugin(
    plugin_id: str,
    organisation_id: str,
    plugin_service: PluginService = Depends(get_plugin_service),
) -> PluginType:
    try:
        with plugin_service as p:
            return p.by_plugin_id(plugin_id, organisation_id)
    except KeyError:
        raise HTTPException(HTTP_404_NOT_FOUND, "Unknown repository")
    except HTTPError as ex:
        raise HTTPException(ex.response.status_code)


@router.get(
    "/repositories/{repository_id}/plugins",
    response_model=Dict[str, PluginType],
)
def list_repository_plugins(
    repository_id: str,
    organisation_id: str,
    plugin_service: PluginService = Depends(get_plugin_service),
):
    with plugin_service as p:
        return p.repository_plugins(repository_id, organisation_id)


@router.get("/repositories/{repository_id}/plugins/{plugin_id}", response_model=PluginType)
def get_repository_plugin(
    plugin_id: str,
    repository_id: str,
    organisation_id: str,
    plugin_service: PluginService = Depends(get_plugin_service),
) -> PluginType:
    try:
        with plugin_service as p:
            return p.repository_plugin(repository_id, plugin_id, organisation_id)
    except KeyError:
        raise HTTPException(HTTP_404_NOT_FOUND, "Unknown repository")
    except HTTPError as ex:
        raise HTTPException(ex.response.status_code)


@router.patch("/repositories/{repository_id}/plugins/{plugin_id}")
def update_plugin_state(
    plugin_id: str,
    repository_id: str,
    organisation_id: str,
    enabled: bool = Body(False, embed=True),
    plugin_service: PluginService = Depends(get_plugin_service),
):
    try:
        with plugin_service as p:
            p.update_by_id(repository_id, plugin_id, organisation_id, enabled)
    except KeyError:
        raise HTTPException(HTTP_404_NOT_FOUND, "Unknown repository")
    except HTTPError as ex:
        raise HTTPException(ex.response.status_code)


@router.get("/plugins/{plugin_id}/schema.json", include_in_schema=False)
def get_plugin_schema(
    plugin_id: str,
    plugin_service: PluginService = Depends(get_plugin_service),
) -> JSONResponse:  # TODO: support for plugin covers in plugin repositories (?)
    try:
        with plugin_service as p:
            return JSONResponse(p.schema(plugin_id))
    except KeyError:
        raise HTTPException(HTTP_404_NOT_FOUND, "Unknown repository")
    except HTTPError as ex:
        raise HTTPException(ex.response.status_code)


@router.get("/plugins/{plugin_id}/cover.jpg", include_in_schema=False)
def get_plugin_cover(
    plugin_id: str,
    plugin_service: PluginService = Depends(get_plugin_service),
) -> FileResponse:  # TODO: support for plugin covers in plugin repositories (?)
    try:
        with plugin_service as p:
            return FileResponse(p.cover(plugin_id))
    except KeyError:
        raise HTTPException(HTTP_404_NOT_FOUND, "Unknown repository")
    except HTTPError as ex:
        raise HTTPException(ex.response.status_code)


@router.get("/plugins/{plugin_id}/description.md", include_in_schema=False)
def get_plugin_description(
    plugin_id: str,
    organisation_id: str,
    plugin_service: PluginService = Depends(get_plugin_service),
) -> Response:  # TODO: support for markdown descriptions in plugin repositories (?)
    try:
        with plugin_service as p:
            return Response(p.description(plugin_id, organisation_id))
    except KeyError:
        raise HTTPException(HTTP_404_NOT_FOUND, "Unknown repository")
    except HTTPError as ex:
        raise HTTPException(ex.response.status_code)


@router.post("/settings/clone/{to_organisation_id}")
def clone_organisation_settings(
    organisation_id: str,
    to_organisation_id: str,
    storage: PluginService = Depends(get_plugin_service),
):
    with storage as store:
        store.clone_settings_to_organisation(organisation_id, to_organisation_id)
