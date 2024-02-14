from fastapi import APIRouter, Depends, HTTPException, status

from boefjes.katalogus.dependencies.repositories import get_repository_store
from boefjes.katalogus.models import RESERVED_LOCAL_ID, Repository
from boefjes.katalogus.routers.organisations import check_organisation_exists
from boefjes.katalogus.storage.interfaces import RepositoryStorage

router = APIRouter(
    prefix="/organisations/{organisation_id}/repositories",
    tags=["repositories"],
    dependencies=[Depends(check_organisation_exists)],
)


@router.get("", response_model=dict[str, Repository], response_model_exclude={0: {0: False}})
def list_repositories(storage: RepositoryStorage = Depends(get_repository_store)):
    return storage.get_all()


@router.get("/{repository_id}", response_model=Repository)
def get_repository(repository_id: str, storage: RepositoryStorage = Depends(get_repository_store)):
    try:
        return storage.get_by_id(repository_id)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown repository")


@router.post("/", status_code=status.HTTP_201_CREATED)
def add_repository(
    repository: Repository,
    storage: RepositoryStorage = Depends(get_repository_store),
):
    with storage as store:
        store.create(repository)


@router.delete("/{repository_id}")
def remove_repository(
    repository_id: str,
    storage: RepositoryStorage = Depends(get_repository_store),
):
    if repository_id == RESERVED_LOCAL_ID:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "LOCAL repository cannot be deleted")
    with storage as store:
        store.delete_by_id(repository_id)
