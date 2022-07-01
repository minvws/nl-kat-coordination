from typing import Dict

from fastapi import APIRouter, status, Depends, HTTPException

from katalogus.dependencies.repositories import get_repository_store
from katalogus.models import Repository
from katalogus.routers.organisations import check_organisation_exists
from katalogus.storage.interfaces import RepositoryStorage


router = APIRouter(
    prefix="/organisations/{organisation_id}/repositories",
    tags=["repositories"],
    dependencies=[Depends(check_organisation_exists)],
)


@router.get(
    "", response_model=Dict[str, Repository], response_model_exclude={0: {0: False}}
)
def list_repositories(storage: RepositoryStorage = Depends(get_repository_store)):
    return storage.get_all()


@router.get("/{repository_id}", response_model=Repository)
def get_repository(
    repository_id: str, storage: RepositoryStorage = Depends(get_repository_store)
):
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
    with storage as store:
        store.delete_by_id(repository_id)
