#!/usr/bin/env python

import json
import logging
from typing import Any

import click
from xtdb_client import XTDBClient

logger = logging.getLogger(__name__)


@click.group(
    context_settings={
        "help_option_names": ["-h", "--help"],
        "max_content_width": 120,
        "show_default": True,
    }
)
@click.option("-n", "--node", default="0", help="XTDB node")
@click.option(
    "-u",
    "--url",
    default="http://localhost:3000",
    help="XTDB server base url",
)
@click.option(
    "-t",
    "--timeout",
    type=int,
    default=5000,
    help="XTDB request timeout (in ms)",
)
@click.option("-v", "--verbosity", count=True, help="Increase the verbosity level")
@click.pass_context
def cli(ctx: click.Context, url: str, node: str, timeout: int, verbosity: int):
    verbosities = [logging.WARN, logging.INFO, logging.DEBUG]
    try:
        if verbosity:
            logging.basicConfig(level=verbosities[verbosity - 1])
    except IndexError:
        raise click.UsageError("Invalid verbosity level (use -v, -vv, or -vvv)")

    client = XTDBClient(url, node, timeout)
    logger.info("Instantiated XTDB client with endpoint %s for node %s", url, node)

    ctx.ensure_object(dict)
    ctx.obj["client"] = client


QY = '{:query {:find [(pull ?var [*])] :where [[?var :type "Origin"][?var :origin_type "observation"][?var :method]]}}'


def method_query(method: str):
    if method:
        return f"""{{
:query {{
    :find [(pull ?var [*])] :where [
            [?var :type "Origin"]
            [?var :origin_type "observation"]
            [?var :method "{method}"]
        ]
    }}
}}
"""
    else:
        return QY


@cli.command(help="List observation origins based on method")
@click.argument("method", required=False)
@click.pass_context
def LIST(ctx: click.Context, method: str):
    origins = ctx.obj["client"].query(method_query(method))
    if not origins:
        raise click.UsageError("No targets found")
    if "error" in origins:
        raise click.UsageError(origins["error"])
    click.echo(json.dumps(origins))


def search_replace_method(ds: list[dict[str, Any]], s: str, r: str):
    for d in ds:
        for k in ["method", "xt/id"]:
            if k in d and s in d[k]:
                d[k] = d[k].replace(s, r)


@cli.command(help="Rename an observation origin method")
@click.option("--armed", is_flag=True, help="Arm the tool to overwrite the method name (confirmation)")
@click.option("--evict", is_flag=True, help="Also remove the history of targeted origins")
@click.argument("method")
@click.argument("renamed")
@click.pass_context
def rename(ctx: click.Context, armed: bool, evict: bool, method: str, renamed: str):
    origins = ctx.obj["client"].query(method_query(method))
    if not origins:
        raise click.UsageError("No targets found")
    if "error" in origins:
        raise click.UsageError(origins["error"])
    if armed:
        operation = "evict" if evict else "delete"
        evict_txs = [f'["{operation}", "{o[0]["xt/id"]}"]' for o in origins]
        search_replace_method([o[0] for o in origins], method, renamed)
        put_txs = [f'["put", {json.dumps(o[0])}]' for o in origins]
        click.echo(json.dumps(ctx.obj["client"].submit_tx(evict_txs + put_txs)))
    else:
        search_replace_method([o[0] for o in origins], method, renamed)
        click.echo(json.dumps(origins))


if __name__ == "__main__":
    cli()
