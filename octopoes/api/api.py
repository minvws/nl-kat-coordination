import logging
from logging import config

import yaml
from fastapi import FastAPI, status
from fastapi.exceptions import RequestValidationError
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi_utils.timing import add_timing_middleware
from requests import RequestException

from octopoes.api.router import router
from octopoes.config.settings import Settings
from octopoes.models.exception import ObjectNotFoundException

settings = Settings()
logger = logging.getLogger(__name__)

# Load log config
try:
    with open(settings.log_cfg, "r") as log_config:
        config.dictConfig(yaml.safe_load(log_config))
        logger.info(f"Configured loggers with config: {settings.log_cfg}")
except FileNotFoundError:
    logger.warning(f"No log config found at: {settings.log_cfg}")

app = FastAPI()
add_timing_middleware(app, record=logger.debug, prefix="app")


@app.exception_handler(RequestValidationError)
def http_exception_handler(request: Request, exc: RequestException):
    logger.critical(exc)
    return JSONResponse(
        {
            "value": str(exc),
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


@app.exception_handler(RequestException)
def http_exception_handler(request: Request, exc: RequestException):
    logger.critical(exc)
    return JSONResponse(
        {
            "value": str(exc),
        },
        status.HTTP_502_BAD_GATEWAY,
    )


@app.exception_handler(ObjectNotFoundException)
def not_found_exception_handler(request: Request, exc: ObjectNotFoundException):
    logger.info(exc)
    return JSONResponse(
        {
            "value": exc.value,
        },
        status.HTTP_404_NOT_FOUND,
    )


@app.exception_handler(Exception)
def uncaught_exception_handler(request: Request, exc: Exception):
    logger.critical(exc)
    return JSONResponse(
        {
            "value": f"{exc.__class__.__name__}: {exc}",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


app.include_router(router)
