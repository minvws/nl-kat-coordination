from fastapi import APIRouter, Depends, HTTPException, status

from boefjes.katalogus.dependencies.organisations import get_organisations_store
from boefjes.katalogus.models import Organisation
from boefjes.katalogus.storage.interfaces import (
    OrganisationNotFound,
    OrganisationStorage,
)
from boefjes.sql.db import ObjectNotFoundException

router = APIRouter(prefix="/organisations", tags=["organisations"])


def check_organisation_exists(
    organisation_id: str,
    storage: OrganisationStorage = Depends(get_organisations_store),
) -> None:
    """
    Checks if an organisation exists, if not, creates it.
    """
    with storage as store:
        try:
            store.get_by_id(organisation_id)
        except OrganisationNotFound:
            add_organisation(Organisation(id=organisation_id, name=organisation_id), storage)
            storage.get_by_id(organisation_id)


@router.get("", response_model=dict[str, Organisation])
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
