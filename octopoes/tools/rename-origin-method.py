#!/usr/bin/env python

import json
import logging

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


@cli.command(help="List observation origins based on method")
@click.argument("method", required=False)
@click.pass_context
def list(ctx: click.Context, method: str):  # noqa: A001
    if method:
        query = f'{{:query {{:find [(pull ?var [*])] :where [[?var :type "Origin"][?var :origin_type "observation"][?var :method "{method}"]]}}}}'  # noqa: E501
    else:
        query = '{:query {:find [(pull ?var [*])] :where [[?var :type "Origin"][?var :origin_type "observation"][?var :method]]}}'  # noqa: E501
    origins = ctx.obj["client"].query(query)
    if not origins:
        raise click.UsageError("No targets found")
    if "error" in origins:
        raise click.UsageError(origins["error"])
    click.echo(json.dumps(origins))


def search_replace_in_dict(ds, s: str, r: str):
    for d in ds:
        for k, v in d.items():
            if s in v:
                d[k] = v.replace(s, r)


@cli.command(help="Rename an observation origin method")
@click.option("--armed", is_flag=True)
@click.argument("method")
@click.argument("renamed")
@click.pass_context
def rename(ctx: click.Context, armed: bool, method: str, renamed: str):
    query = f'{{:query {{:find [(pull ?var [*])] :where [[?var :type "Origin"][?var :origin_type "observation"][?var :method "{method}"]]}}}}'  # noqa: E501
    origins = ctx.obj["client"].query(query)
    if not origins:
        raise click.UsageError("No targets found")
    if "error" in origins:
        raise click.UsageError(origins["error"])
    if armed:
        evict_txs = [f"[\"evict\", \"{o[0]["xt/id"]}\"]" for o in origins]
        search_replace_in_dict([x[0] for x in origins], method, renamed)
        put_txs = [f'["put", {json.dumps(o[0])}]' for o in origins]
        click.echo(ctx.obj["client"].submit_tx(evict_txs + put_txs))
    else:
        search_replace_in_dict([x[0] for x in origins], method, renamed)
        click.echo(json.dumps(origins))


if __name__ == "__main__":
    cli()
