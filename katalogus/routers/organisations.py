from fastapi import HTTPException

from typing import Dict

from fastapi import APIRouter, status, Depends

from katalogus.dependencies.organisations import get_organisations_store
from katalogus.models import Organisation
from katalogus.storage.interfaces import OrganisationStorage
from sql.db import ObjectNotFoundException

router = APIRouter(prefix="/organisations", tags=["organisations"])


def check_organisation_exists(
    organisation_id: str,
    storage: OrganisationStorage = Depends(get_organisations_store),
) -> None:
    """
    Raises OrganisationNotFound when the organisation_id does not exist, which in turn
    is handled by the organisation_not_found_handler()
    """
    with storage as store:
        store.get_by_id(organisation_id)


@router.get("", response_model=Dict[str, Organisation])
def list_organisations(
    storage: OrganisationStorage = Depends(get_organisations_store),
):
    return storage.get_all()


@router.get("/{organisation_id}", response_model=Organisation)
def get_organisation(
    organisation_id: str,
    storage: OrganisationStorage = Depends(get_organisations_store),
):
    try:
        return storage.get_by_id(organisation_id)
    except (KeyError, ObjectNotFoundException):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown organisation")


@router.post("/", status_code=status.HTTP_201_CREATED)
def add_organisation(
    organisation: Organisation,
    storage: OrganisationStorage = Depends(get_organisations_store),
):
    with storage as store:
        store.create(organisation)


@router.delete("/{organisation_id}")
def remove_organisation(
    organisation_id: str,
    storage: OrganisationStorage = Depends(get_organisations_store),
):
    with storage as store:
        store.delete_by_id(organisation_id)
