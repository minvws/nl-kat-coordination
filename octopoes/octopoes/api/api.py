import logging
import socket
from logging import config
from pathlib import Path

import yaml
from fastapi import FastAPI, status
from fastapi.exceptions import RequestValidationError
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pika.adapters.utils.connection_workflow import AMQPConnectionWorkflowFailed
from requests import RequestException

from octopoes.api.models import ServiceHealth
from octopoes.api.router import router
from octopoes.config.settings import Settings
from octopoes.core.app import close_rabbit_channel
from octopoes.events.manager import get_rabbit_channel
from octopoes.models.exception import ObjectNotFoundException
from octopoes.version import __version__

settings = Settings()
logger = logging.getLogger(__name__)

# Load log config
try:
    with Path(settings.log_cfg).open() as log_config:
        config.dictConfig(yaml.safe_load(log_config))
        logger.info("Configured loggers with config: %s", settings.log_cfg)
except FileNotFoundError:
    logger.warning("No log config found at: %s", settings.log_cfg)


app = FastAPI()

# Set up OpenTelemetry instrumentation
if settings.span_export_grpc_endpoint is not None:
    logger.info("Setting up instrumentation with span exporter endpoint [%s]", settings.span_export_grpc_endpoint)

    FastAPIInstrumentor.instrument_app(app)
    RequestsInstrumentor().instrument()

    resource = Resource(attributes={SERVICE_NAME: "octopoes"})
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.span_export_grpc_endpoint))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    logger.debug("Finished setting up instrumentation")


@app.exception_handler(RequestValidationError)
def http_validation_exception_handler(request: Request, exc: RequestException) -> JSONResponse:
    logger.critical(exc)
    return JSONResponse(
        {
            "value": str(exc),
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


@app.exception_handler(RequestException)
def http_exception_handler(request: Request, exc: RequestException) -> JSONResponse:
    logger.critical(exc)
    return JSONResponse(
        {
            "value": str(exc),
        },
        status.HTTP_502_BAD_GATEWAY,
    )


@app.exception_handler(ObjectNotFoundException)
def not_found_exception_handler(request: Request, exc: ObjectNotFoundException) -> JSONResponse:
    logger.info(exc)
    return JSONResponse(
        {
            "value": exc.value,
        },
        status.HTTP_404_NOT_FOUND,
    )


@app.exception_handler(Exception)
def uncaught_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.critical(exc)
    return JSONResponse(
        {
            "value": f"{exc.__class__.__name__}: {exc}",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


@app.get("/health")
def root_health() -> ServiceHealth:
    return ServiceHealth(
        service="octopoes",
        healthy=True,
        version=__version__,
    )


@app.on_event("shutdown")
def close_rabbit_mq_connection():
    close_rabbit_channel(settings.queue_uri)


@app.on_event("startup")
def create_rabbit_mq_connection():
    try:
        get_rabbit_channel(settings.queue_uri)
    except (AMQPConnectionWorkflowFailed, socket.gaierror):
        logger.exception("Unable to connect RabbitMQ on startup")


app.include_router(router)
