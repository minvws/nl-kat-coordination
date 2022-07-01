from typing import Dict, List

from fastapi import APIRouter, Depends, Body, HTTPException
from requests import HTTPError
from starlette.responses import FileResponse, Response
from starlette.status import HTTP_404_NOT_FOUND

from katalogus.dependencies.plugins import PluginService, get_plugin_service
from katalogus.models import PluginType
from katalogus.routers.organisations import check_organisation_exists


router = APIRouter(
    prefix="/organisations/{organisation_id}",
    tags=["plugins"],
    dependencies=[Depends(check_organisation_exists)],
)


@router.get("/plugins", response_model=List[PluginType])
def list_plugins(
    organisation_id: str,
    plugin_service: PluginService = Depends(get_plugin_service),
) -> List[PluginType]:
    with plugin_service as p:
        return p.get_all(organisation_id)


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


@router.get(
    "/repositories/{repository_id}/plugins/{plugin_id}", response_model=PluginType
)
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


@router.get("/plugins/{plugin_id}/cover.png", include_in_schema=False)
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
