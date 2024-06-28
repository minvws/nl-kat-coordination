import structlog

structlog.get_logger(__name__).warning(
    "This module has been phased out in v1.16.0 and will be removed in v1.17.0"
)
