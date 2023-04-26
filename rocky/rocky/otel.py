import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)


class OpenTelemetryHelper:
    """
    Helper class to set up OpenTelemetry instrumentation.
    """

    @staticmethod
    def setup_instrumentation(span_export_grpc_endpoint):
        logger.info("Setting up instrumentation with span exporter endpoint [%s]", span_export_grpc_endpoint)

        DjangoInstrumentor().instrument()
        Psycopg2Instrumentor().instrument()
        RequestsInstrumentor().instrument()

        resource = Resource(attributes={SERVICE_NAME: "rocky"})
        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=span_export_grpc_endpoint))
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        logger.debug("Finished setting up instrumentation")
