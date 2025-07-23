from opentelemetry import trace

tracer = trace.get_tracer(__name__)


class OTELInstrumentTemplateMiddleware:
    """
    Django middleware to instrument template rendering using OpenTelemetry
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_template_response(self, request, response):
        if hasattr(response, "render") and callable(response.render):
            # get the original render method
            original_render = response.render

            # create a span to trace the template rendering
            tracer = trace.get_tracer(__name__)
            span = tracer.start_span("django.render_template")

            # define the new render method which will close the span
            def traced_render(*args, **kwargs):
                try:
                    return original_render(*args, **kwargs)
                finally:
                    span.end()

            # replace the render method on the response with the new one
            response.render = traced_render

        return response
