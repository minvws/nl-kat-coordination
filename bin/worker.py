import click

from app import app
from config import settings


@click.command()
@click.argument("worker_type", type=click.Choice(["boefje", "normalizer"]))
@click.option("--broker", type=str, help='A broker URI. (e.g. "amqp://localhost")')
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    help="Log level",
    default="WARNING",
)
def cli(worker_type, broker, log_level):
    click.echo(f"Starting worker for {worker_type}")

    if broker:
        app.conf.update({"broker_url": broker})

    if worker_type == "boefje":
        queues = [settings.queue_name_boefjes]
    else:
        queues = [settings.queue_name_normalizers]

    app.worker_main(
        [
            "--app",
            "tasks",
            "worker",
            "--loglevel",
            log_level,
            "--events",
            "--queues",
            queues,
            "--hostname",
            f"{worker_type}@%h",
        ]
    )


if __name__ == "__main__":
    cli()
