"""Keiko CLI module."""
import uuid
from typing import TextIO

import click

from keiko.base_models import ReportArgumentsBase
from keiko.keiko import generate_report
from keiko.logging import setup_loggers
from keiko.settings import Settings


@click.command()
@click.argument("sample", type=click.File("r"))
def main(
    sample: TextIO,
) -> None:
    """
    Click entry point.

    Generate a preprocessed LateX file from a template, a JSON data file and a glossary CSV file.
    """
    settings = Settings()
    setup_loggers(settings)

    report_arguments = ReportArgumentsBase.model_validate_json(sample.read())
    id_ = uuid.uuid4().hex[:8]
    generate_report(
        report_arguments.template,
        report_arguments.data,
        report_arguments.glossary,
        id_,
        report_arguments.debug,
        settings,
    )

    click.echo(f"Report generated with id {id_}")


if __name__ == "__main__":
    # pylint: disable=no-value-for-parameter
    main()
