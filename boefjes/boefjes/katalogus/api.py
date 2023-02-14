import logging

from typing import List, Optional, Any

from fastapi import FastAPI, status, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from boefjes.katalogus.storage.interfaces import StorageError
from boefjes.katalogus.v1 import router
from boefjes.katalogus.version import __version__

app = FastAPI(title="KAT-alogus API", version=__version__)
app.include_router(router, prefix="/v1")


logger = logging.getLogger(__name__)


@app.exception_handler(StorageError)
def entity_not_found_handler(request: Request, exc: StorageError):
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
