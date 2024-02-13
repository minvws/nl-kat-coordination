"""Keiko Web API."""
import logging
import uuid
from pathlib import Path
from typing import List

from fastapi import BackgroundTasks, Body, FastAPI
from fastapi.staticfiles import StaticFiles
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic import BaseModel

from keiko.base_models import ReportArgumentsBase
from keiko.health import ServiceHealth, get_health
from keiko.keiko import generate_report
from keiko.settings import Settings
from keiko.templates import get_samples, get_templates

logger = logging.getLogger(__name__)


def construct_api(settings: Settings) -> FastAPI:
    """Construct the FastAPI object, with prefilled examples from disk."""
    app = FastAPI()

    # Set up OpenTelemetry instrumentation
    if settings.span_export_grpc_endpoint is not None:
        logger.info("Setting up instrumentation with span exporter endpoint [%s]", settings.span_export_grpc_endpoint)

        FastAPIInstrumentor.instrument_app(app)

        resource = Resource(attributes={SERVICE_NAME: "keiko"})
        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=str(settings.span_export_grpc_endpoint)))
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        logger.debug("Finished setting up instrumentation")

    examples = get_samples(settings)

    @app.get("/templates")
    def get_templates_() -> List[str]:
        """Endpoint to list known templates."""
        return list(get_templates(settings))

    class ReportResponse(BaseModel):
        """Response model for the create report endpoint."""

        report_id: str

    @app.post("/reports")
    def create_report(
        parameters: ReportArgumentsBase = Body(..., examples=examples),
        background_tasks: BackgroundTasks = BackgroundTasks(),
    ) -> ReportResponse:
        """Endpoint to generate a report from a template."""
        report_id = str(uuid.uuid4())[:8]

        background_tasks.add_task(
            generate_report,
            template_name=parameters.template,
            report_data=parameters.data,
            glossary=parameters.glossary,
            report_id=report_id,
            debug=parameters.debug,
            settings=settings,
        )

        return ReportResponse(report_id=report_id)

    @app.get("/health")
    def health() -> ServiceHealth:
        """Health endpoint."""
        return get_health()

    # mount reports as static files
    Path(settings.reports_folder).mkdir(parents=True, exist_ok=True)
    app.mount("/reports", StaticFiles(directory=settings.reports_folder), name="reports")

    return app
