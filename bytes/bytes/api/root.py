import logging
from typing import Any, List, Optional, Union

import prometheus_client
from fastapi import APIRouter, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse, Response
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY

from bytes.api.metrics import get_registry
from bytes.auth import TokenResponse, authenticate_token, get_access_token
from bytes.database.sql_meta_repository import create_meta_data_repository
from bytes.repositories.meta_repository import MetaDataRepository
from bytes.version import __version__

router = APIRouter()
logger = logging.getLogger(__name__)


class ServiceHealth(BaseModel):
    service: str
    healthy: bool = False
    version: Optional[str] = None
    additional: Any = None
    results: List["ServiceHealth"] = []


ServiceHealth.update_forward_refs()


def validation_exception_handler(_: Request, exc: Union[RequestValidationError, ValidationError]) -> JSONResponse:
    logger.critical(exc)
    return JSONResponse(
        {
            "value": str(exc),
        },
        HTTP_422_UNPROCESSABLE_ENTITY,
    )


@router.get("/", include_in_schema=False)
def health() -> RedirectResponse:
    return RedirectResponse(url="/health")


@router.get("/health", response_model=ServiceHealth)
def root() -> ServiceHealth:
    bytes_health = ServiceHealth(service="bytes", healthy=True, version=__version__)
    return bytes_health


@router.get("/metrics", dependencies=[Depends(authenticate_token)])
def metrics(meta_repository: MetaDataRepository = Depends(create_meta_data_repository)):
    collector_registry = get_registry(meta_repository)
    data = prometheus_client.generate_latest(collector_registry)

    return Response(media_type="text/plain", content=data)


@router.post("/token", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    access_token, expire_time = get_access_token(form_data)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_at=expire_time.isoformat(),
    )
