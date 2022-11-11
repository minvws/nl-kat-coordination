from typing import Dict

from fastapi import APIRouter, status, Depends, Body, HTTPException

from boefjes.katalogus.dependencies.plugins import PluginService, get_plugin_service
from boefjes.katalogus.routers.organisations import check_organisation_exists

router = APIRouter(
    prefix="/organisations/{organisation_id}/{plugin_id}/settings",
    tags=["settings"],
    dependencies=[Depends(check_organisation_exists)],
)


@router.get("", response_model=Dict[str, str])
def list_settings(
    organisation_id: str,
    plugin_id: str,
    plugin_service: PluginService = Depends(get_plugin_service),
):
    with plugin_service as p:
        return p.get_all_settings(organisation_id, plugin_id)


@router.get("/{key}", response_model=str)
def get_setting(
    key: str,
    organisation_id: str,
    plugin_id: str,
    plugin_service: PluginService = Depends(get_plugin_service),
) -> str:
    try:
        with plugin_service as p:
            return p.get_setting_by_key(key, organisation_id, plugin_id)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown key")


@router.post("/{key}", status_code=status.HTTP_201_CREATED)
def add_setting(
    key: str,
    organisation_id: str,
    plugin_id: str,
    value: str = Body("", embed=True),
    plugin_service: PluginService = Depends(get_plugin_service),
):
    with plugin_service as p:
        p.create_setting(key, value, organisation_id, plugin_id)


@router.delete("/{key}")
def remove_setting(
    key: str,
    organisation_id: str,
    plugin_id: str,
    plugin_service: PluginService = Depends(get_plugin_service),
):
    with plugin_service as p:
        p.delete_setting_by_key(key, organisation_id, plugin_id)


@router.put("/{key}")
def update_setting(
    key: str,
    organisation_id: str,
    plugin_id: str,
    value: str = Body("", embed=True),
    plugin_service: PluginService = Depends(get_plugin_service),
):
    with plugin_service as p:
        p.update_setting_by_key(key, value, organisation_id, plugin_id)
