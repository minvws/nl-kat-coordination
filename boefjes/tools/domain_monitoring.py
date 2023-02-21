#!/usr/bin/python3

import datetime
import io
import json
import logging
import logging.handlers
import queue
import threading
import uuid
from enum import Enum
from typing import Set, Tuple, List, Sequence, Any, NoReturn

import certstream
import click
import tldextract

from boefjes.clients.bytes_client import BytesAPIClient
from boefjes.job_models import BoefjeMeta, Boefje

IGNORE_LIST = ("", "*", "www", "dev", "acc", "staging")  # ignore common stuff, cleans up the lists for speed
MIN_LENGTH = 3  # ignore parts that are too small


class MatchType(Enum):
    DIRECT = "direct"
    SUPERSTRING = "superstring"
    SUBSTRING = "substring"


class ExtendedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, MatchType):
            return o.value

        return super().default(o)


class MessageQueue:
    def __init__(self, client: BytesAPIClient, queue_size=1000, interval=datetime.timedelta(hours=2)):
        self._client = client
        self._messages = queue.Queue(maxsize=queue_size)
        self._interval = interval
        self._logger = logging.getLogger("MessageQueue")
        self._timer = None
        self.start_timer()

    # create and start timer
    def start_timer(self) -> None:
        # cancel timer if it exists or already running
        if self._timer is not None:
            self._timer.cancel()

        self._timer = threading.Timer(self._interval.total_seconds(), self._timer_callback)
        self._timer.daemon = True  # make sure the timer thread is killed when the main thread is killed
        self._logger.info("Started timer with interval of %d seconds", self._interval.total_seconds())
        self._timer.start()

    def _timer_callback(self) -> None:
        self._logger.info("Timed out, flushing queue")
        self.flush()

    def enqueue(self, message: Any) -> None:
        try:
            self._messages.put_nowait(message)
        except queue.Full:
            self._logger.info("Queue is full")
            self.flush()
            self._messages.put_nowait(message)

    def flush(self) -> None:
        if not self._messages.empty():
            self._logger.info("Flushing queue (%d messages)", self._messages.qsize())
            stream = io.BytesIO()

            # write all messages to the stream as jsonlines
            while not self._messages.empty():
                message = self._messages.get_nowait()
                stream.write(json.dumps(message, cls=ExtendedJSONEncoder).encode("utf-8") + b"\r\n")

            # save the stream to bytes
            self._logger.info("Saving stream to bytes (%d bytes)", stream.tell())
            meta = BoefjeMeta(
                id=str(uuid.uuid4()),
                boefje=Boefje(id="domain-monitoring", version="0.1"),
                organization="",
                started_at=datetime.datetime.now(datetime.timezone.utc),
                ended_at=datetime.datetime.now(datetime.timezone.utc),
            )
            self._client.save_boefje_meta(meta)
            self._client.save_raw(meta.id, stream.getvalue(), {"application/jsonlines"})
            self._logger.info("Saved stream to bytes")

        else:
            self._logger.warning("Queue is empty, skipping flush")

        self.start_timer()


def domains_match(input_domains: Set[str], domains: Sequence[str]) -> List[Tuple[MatchType, str]]:
    matches = []

    for input_domain in input_domains:
        input_domain_without_tld = extract_domain(input_domain)

        for domain in domains:
            tokenized_domain = tokenize_domain(domain)

            # check for direct matches against domains
            if input_domain_without_tld in tokenized_domain:
                matches.append((MatchType.DIRECT, domain))

            # remove direct matches and check for substring matches against domains
            diff_tokenized_domain = set(tokenized_domain).difference([input_domain_without_tld])
            for part in diff_tokenized_domain:
                if input_domain_without_tld in part:
                    matches.append((MatchType.SUBSTRING, domain))

    return matches


# extract domain
def extract_domain(domain: str) -> str:
    # returns domain without suffix and subdomain
    return tldextract.extract(domain.lower()).domain


# tokenize domain
def tokenize_domain(domain: str) -> List[str]:
    # returns list of subdomains and domain without suffix
    result = tldextract.extract(domain.lower())

    return [sub for sub in result.subdomain.split(".") if len(sub) >= MIN_LENGTH and sub not in IGNORE_LIST] + [
        result.domain
    ]


class Monitor:
    def __init__(
        self,
        input_domains: Set[str],
        client: BytesAPIClient,
        message_queue: MessageQueue,
        stream_url,
    ):
        self._input_domains = input_domains
        self._stream_url = stream_url
        self._client = client
        self._queue = message_queue
        self._logger = logging.getLogger("Monitor")

    def start(self) -> None:
        self._logger.info("Logging in to Bytes API")
        try:
            self._client.login()

        except Exception as e:
            self._logger.error("Failed to login to Bytes API: %s", e)

        else:
            self._logger.info("Starting monitor: %s", self._stream_url)
            certstream.listen_for_events(self._message_callback, self._stream_url)
            logging.info("Monitor stopped")
            self._queue.flush()

    def _message_callback(self, message, context) -> None:
        self._logger.debug("Incoming message: %s", message)

        if message["message_type"] == "certificate_update":
            all_domains = message["data"]["leaf_cert"]["all_domains"]

            if all_domains and (match := domains_match(self._input_domains, all_domains)):
                for match_type, match in match:
                    self._logger.info("Match (type %s) found for %s: %s", match_type, match, ", ".join(all_domains))
                    self._queue.enqueue({"match_type": match_type, "match": match, "domains": all_domains})


@click.command()
@click.option("--domains", multiple=True, envvar="DOMAINS", help="Domains to monitor")
@click.option("--size", default=1000, help="Size of the message queue")
@click.option("--interval", type=click.IntRange(1), default=3600, help="Interval in seconds to flush the queue")
@click.option("--bytes-api", default="http://localhost:8002", envvar="BYTES_API", help="Bytes API uri")
@click.option("--bytes-username", help="Bytes API username", envvar="BYTES_USERNAME")
@click.option("--bytes-password", help="Bytes API password", envvar="BYTES_PASSWORD")
@click.option("--stream-url", default="wss://certstream.calidog.io", help="Certstream url")
def main(
    domains: Sequence[str],
    size: int,
    interval: int,
    bytes_api: str,
    bytes_username: str,
    bytes_password: str,
    stream_url: str,
) -> NoReturn:
    domains = set(domains)
    click.echo(f"Domains to check: {', '.join(domains)}")

    client = BytesAPIClient(bytes_api, bytes_username, bytes_password)
    message_queue = MessageQueue(client, size, datetime.timedelta(seconds=interval))
    monitor = Monitor(domains, client, message_queue, stream_url)
    monitor.start()


if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)s %(levelname)7s [%(name)15s]: %(message)s", level=logging.INFO)

    main()
