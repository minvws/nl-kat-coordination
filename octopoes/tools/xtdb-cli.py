#!/usr/bin/env python

import datetime
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


@cli.command
@click.pass_context
def status(ctx: click.Context):
    client: XTDBClient = ctx.obj["client"]

    click.echo(json.dumps(client.status()))


@cli.command(help='EDN Query (default: "{:query {:find [ ?var ] :where [[?var :xt/id ]]}}")')
@click.argument("edn", required=False)
@click.pass_context
def query(ctx: click.Context, edn: str):
    client: XTDBClient = ctx.obj["client"]

    if edn:
        click.echo(json.dumps(client.query(edn)))
    else:
        click.echo(json.dumps(client.query()))


@cli.command(help="List all keys in node")
@click.pass_context
def list_keys(ctx: click.Context):
    client: XTDBClient = ctx.obj["client"]

    click.echo(json.dumps(client.query()))


@cli.command(help="List all values in node")
@click.pass_context
def list_values(ctx: click.Context):
    client: XTDBClient = ctx.obj["client"]

    click.echo(json.dumps(client.query("{:query {:find [(pull ?var [*])] :where [[?var :xt/id]]}}")))


@cli.command
@click.option("--tx-id", type=int)
@click.option("--tx-time", type=click.DateTime())
@click.option("--valid-time", type=click.DateTime())
@click.argument("key")
@click.pass_context
def entity(
    ctx: click.Context,
    key: str,
    valid_time: datetime.datetime | None = None,
    tx_time: datetime.datetime | None = None,
    tx_id: int | None = None,
):
    client: XTDBClient = ctx.obj["client"]

    click.echo(json.dumps(client.entity(key, valid_time, tx_time, tx_id)))


@cli.command
@click.option("--with-docs", is_flag=True)
@click.option("--with-corrections", is_flag=True)
@click.argument("key")
@click.pass_context
def history(ctx: click.Context, key: str, with_corrections: bool, with_docs: bool):
    client: XTDBClient = ctx.obj["client"]

    click.echo(json.dumps(client.history(key, with_corrections, with_docs)))


@cli.command
@click.option("--tx-id", type=int)
@click.option("--tx-time", type=click.DateTime())
@click.option("--valid-time", type=click.DateTime())
@click.argument("key")
@click.pass_context
def entity_tx(
    ctx: click.Context,
    key: str,
    valid_time: datetime.datetime | None = None,
    tx_time: datetime.datetime | None = None,
    tx_id: int | None = None,
):
    client: XTDBClient = ctx.obj["client"]

    click.echo(json.dumps(client.entity_tx(key, valid_time, tx_time, tx_id)))


@cli.command
@click.pass_context
def attribute_stats(ctx: click.Context):
    client: XTDBClient = ctx.obj["client"]

    click.echo(json.dumps(client.attribute_stats()))


@cli.command
@click.option("--timeout", type=int)
@click.pass_context
def sync(ctx: click.Context, timeout: int | None):
    client: XTDBClient = ctx.obj["client"]

    click.echo(json.dumps(client.sync(timeout)))


@cli.command
@click.option("--timeout", type=int)
@click.argument("tx-id", type=int)
@click.pass_context
def await_tx(ctx: click.Context, tx_id: int, timeout: int | None):
    client: XTDBClient = ctx.obj["client"]

    click.echo(json.dumps(client.await_tx(tx_id, timeout)))


@cli.command
@click.option("--timeout", type=int)
@click.argument("tx-time", type=click.DateTime())
@click.pass_context
def await_tx_time(
    ctx: click.Context,
    tx_time: datetime.datetime,
    timeout: int | None,
):
    client: XTDBClient = ctx.obj["client"]

    click.echo(json.dumps(client.await_tx_time(tx_time, timeout)))


@cli.command
@click.option("--with-ops", is_flag=True)
@click.option("--after-tx-id", type=int)
@click.pass_context
def tx_log(ctx: click.Context, after_tx_id: int | None, with_ops: bool):
    client: XTDBClient = ctx.obj["client"]

    click.echo(json.dumps(client.tx_log(after_tx_id, with_ops)))


@cli.command(help="Show all document transactions")
@click.pass_context
def txs(ctx: click.Context):
    client: XTDBClient = ctx.obj["client"]

    click.echo(json.dumps(client.tx_log(None, True)))


@cli.command
@click.argument("txs", nargs=-1)
@click.pass_context
def submit_tx(ctx: click.Context, txs):
    client: XTDBClient = ctx.obj["client"]

    click.echo(json.dumps(client.submit_tx(txs)))


@cli.command
@click.argument("tx-id", type=int)
@click.pass_context
def tx_committed(ctx: click.Context, tx_id: int) -> None:
    client: XTDBClient = ctx.obj["client"]

    click.echo(json.dumps(client.tx_committed(tx_id)))


@cli.command
@click.pass_context
def latest_completed_tx(ctx: click.Context):
    client: XTDBClient = ctx.obj["client"]

    click.echo(json.dumps(client.latest_completed_tx()))


@cli.command
@click.pass_context
def latest_submitted_tx(ctx: click.Context):
    client: XTDBClient = ctx.obj["client"]

    click.echo(json.dumps(client.latest_submitted_tx()))


@cli.command
@click.pass_context
def active_queries(ctx: click.Context):
    client: XTDBClient = ctx.obj["client"]

    click.echo(json.dumps(client.active_queries()))


@cli.command
@click.pass_context
def recent_queries(ctx: click.Context):
    client: XTDBClient = ctx.obj["client"]

    click.echo(json.dumps(client.recent_queries()))


@cli.command
@click.pass_context
def slowest_queries(ctx: click.Context):
    client: XTDBClient = ctx.obj["client"]

    click.echo(json.dumps(client.slowest_queries()))


if __name__ == "__main__":
    cli()
