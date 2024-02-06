import logging.config

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic import ValidationError

from bytes.api.root import router as root_router
from bytes.api.root import validation_exception_handler
from bytes.api.router import router
from bytes.config import get_settings

logger = logging.getLogger(__name__)

logging.config.fileConfig(get_settings().log_cfg, disable_existing_loggers=False)

app = FastAPI()

if get_settings().span_export_grpc_endpoint is not None:
    logger.info("Setting up instrumentation with span exporter endpoint [%s]", get_settings().span_export_grpc_endpoint)

    FastAPIInstrumentor.instrument_app(app)
    Psycopg2Instrumentor().instrument()
    RequestsInstrumentor().instrument()

    resource = Resource(attributes={SERVICE_NAME: "bytes"})
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=str(get_settings().span_export_grpc_endpoint)))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    logger.debug("Finished setting up instrumentation")

app.include_router(root_router)
app.include_router(router, prefix="/bytes")
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
