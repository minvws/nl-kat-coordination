from typing import Dict

from fastapi import APIRouter, status, Depends, Body, HTTPException

from katalogus.dependencies.settings import SettingsService, get_settings_service
from katalogus.routers.organisations import check_organisation_exists


router = APIRouter(
    prefix="/organisations/{organisation_id}/settings",
    tags=["settings"],
    dependencies=[Depends(check_organisation_exists)],
)


@router.get("", response_model=Dict[str, str])
def list_settings(
    organisation_id: str, settings: SettingsService = Depends(get_settings_service)
):
    return settings.get_all(organisation_id)


@router.get("/{key}", response_model=str)
def get_setting(
    key: str,
    organisation_id: str,
    settings: SettingsService = Depends(get_settings_service),
) -> str:
    try:
        return settings.get_by_key(key, organisation_id)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown key")


@router.post("/{key}", status_code=status.HTTP_201_CREATED)
def add_setting(
    key: str,
    organisation_id: str,
    value: str = Body("", embed=True),
    settings: SettingsService = Depends(get_settings_service),
):
    settings.create(key, value, organisation_id)


@router.delete("/{key}")
def remove_setting(
    key: str,
    organisation_id: str,
    settings: SettingsService = Depends(get_settings_service),
):
    settings.delete_by_id(key, organisation_id)


@router.put("/{key}")
def update_setting(
    key: str,
    organisation_id: str,
    value: str = Body("", embed=True),
    settings: SettingsService = Depends(get_settings_service),
):
    settings.update_by_id(key, value, organisation_id)
