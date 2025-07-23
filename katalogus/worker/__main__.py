import json
import logging.config
import os
from pathlib import Path

import click
import structlog

from .oci_adapter import run_with_callback

default_log_path = Path(__file__).parent / "logging.json"
logging_format = os.getenv("LOGGING_FORMAT", "text")
log_cfg = Path(os.getenv("LOG_CFG", str(default_log_path.absolute())))

with log_cfg.open() as f:
    logging.config.dictConfig(json.load(f))

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper("iso", utc=False),
        (
            structlog.dev.ConsoleRenderer(colors=True, pad_level=False)
            if logging_format == "text"
            else structlog.processors.JSONRenderer()
        ),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@click.command()
@click.option("-p", "--plugins", type=str, default=None, multiple=True, help="A list of plugin ids to filter on.")
@click.option(
    "-l", "--log-level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]), help="Log level", default="INFO"
)
@click.argument("input_url", default="")
def cli(plugins: tuple[str] | None, log_level: str, input_url: str) -> None:
    logger.setLevel(log_level)
    logger.info("Starting runtime")

    return run_with_callback(input_url)


if __name__ == "__main__":
    cli()
