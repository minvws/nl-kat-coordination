import logging

from typing import List, Optional, Any

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import JSONResponse, Response, FileResponse, RedirectResponse
from pydantic import BaseModel

from boefjes.models import BOEFJES_DIR, Boefje
from katalogus.boefjes import BoefjeResource, resolve_boefjes, to_resource
from katalogus.storage.interfaces import StorageError
from katalogus.v1 import router
from katalogus.version import __version__

app = FastAPI(title="KAT-alogus API", version=__version__)
app.include_router(router, prefix="/v1")


logger = logging.getLogger(__name__)


@app.exception_handler(StorageError)
def organisation_not_found_handler(request: Request, exc: StorageError):
    logger.exception("some error", exc_info=exc)

    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"message": exc.message},
    )


class ServiceHealth(BaseModel):
    service: str
    healthy: bool = False
    version: Optional[str] = None
    additional: Any = None
    results: List["ServiceHealth"] = []


ServiceHealth.update_forward_refs()


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/health")


@app.get("/health", response_model=ServiceHealth)
def health() -> ServiceHealth:
    return ServiceHealth(service="katalogus", healthy=True, version=__version__)


@app.get("/boefjes", response_model=List[BoefjeResource], deprecated=True)
def list_boefjes() -> List[BoefjeResource]:
    boefjes = resolve_boefjes(BOEFJES_DIR)

    return [to_resource(boefje) for boefje in boefjes.values()]


@app.get("/boefjes/{boefje_id}", response_model=BoefjeResource, deprecated=True)
def get_boefje(boefje_id: str) -> BoefjeResource:
    boefje = get_boefje_or_404(boefje_id)

    return to_resource(boefje)


@app.get("/boefjes/{boefje_id}/cover.png", include_in_schema=False, deprecated=True)
def get_boefje_cover(boefje_id: str) -> Response:
    boefje = get_boefje_or_404(boefje_id)
    parent, _ = boefje.module.split(".", maxsplit=1)
    path = BOEFJES_DIR / parent / "cover.png"

    if not path.exists():
        path = BOEFJES_DIR / "default_cover.png"

    return FileResponse(path)


@app.get(
    "/boefjes/{boefje_id}/description.md", include_in_schema=False, deprecated=True
)
def get_boefje_description(boefje_id: str) -> Response:
    boefje = get_boefje_or_404(boefje_id)
    parent, _ = boefje.module.split(".", maxsplit=1)
    path = BOEFJES_DIR / parent / "description.md"

    return FileResponse(path)


def get_boefje_or_404(boefje_id: str) -> Boefje:
    boefjes = resolve_boefjes(BOEFJES_DIR)

    if boefje_id not in boefjes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Boefje not found"
        )

    return boefjes[boefje_id]
