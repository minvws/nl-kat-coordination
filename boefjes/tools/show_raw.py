#!/usr/bin/env python3
# ruff: noqa: E402, T201

import json
import sys
from pathlib import Path

import click
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import JsonLexer

sys.path.append(str(Path(__file__).resolve().parent.parent))

from boefjes.job_handler import bytes_api_client


@click.command()
@click.option("--json", "print_json", is_flag=True, help="Pretty print raw as json")
@click.argument("raw_id")
def show_raw(print_json, raw_id):
    """Show raw file"""

    bytes_api_client.login()
    raw = bytes_api_client.get_raw(raw_id)

    raw_str = raw.decode("utf-8")

    if print_json:
        json_object = json.loads(raw_str)
        formatted_json_str = json.dumps(json_object, indent=4, sort_keys=True)
        print(highlight(formatted_json_str, JsonLexer(), TerminalFormatter()))
    else:
        print(raw_str)


if __name__ == "__main__":
    show_raw()
