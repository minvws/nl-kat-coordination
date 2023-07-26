import io
import logging
import os
import tarfile
from typing import ByteString, Generator, List, Tuple, Union

import docker

from boefjes.job_models import BoefjeMeta

IMAGE = "ghcr.io/minvws/nl-kat-masscan-build-image:latest"
FILE_PATH = "/tmp/output.json"


###############################################################################
# Identical to Webpage Capture boefje.
###############################################################################
class TarStream(io.RawIOBase):
    """Wrapper around generator to feed tarfile.

    Based on:
    - https://stackoverflow.com/questions/39155958/how-do-i-read-a-tarfile-from-a-generator
    - https://stackoverflow.com/questions/6657820/how-to-convert-an-iterable-to-a-stream/6658949
    """

    def __init__(self, stream: Generator):
        """Store the generator in the TarStream class."""
        self.bytes_left = None
        self.stream = stream
        self.able_to_read = bool(stream)
        super().__init__()

    def reader(self) -> io.BufferedReader:
        """Return the bufferedreader for this TarStream."""
        return io.BufferedReader(self)

    def readable(self) -> bool:
        """Returns whether the generator stream is (still) readable."""
        return self.able_to_read

    def readinto(self, memory_view: ByteString) -> int:
        """Read the generator. Returns 0 when done. Output is stored in memory_view."""
        try:
            chunk = self.bytes_left or next(self.stream)
        except StopIteration:
            self.able_to_read = False
            return 0
        view_len = len(memory_view)
        output, self.bytes_left = chunk[:view_len], chunk[view_len:]
        outlen = len(output)
        memory_view[:outlen] = output
        return outlen


def get_file_from_container(container: docker.models.containers.Container, path: str) -> Union[bytes, None]:
    """Returns a file from a docker container."""
    try:
        stream, _ = container.get_archive(path)
    except docker.errors.NotFound:
        logging.warning(
            "[Masscan] %s not found in container %s %s",
            path,
            container.short_id,
            container.image.tags,
        )
        return None

    f = tarfile.open(mode="r|", fileobj=TarStream(stream).reader())
    tarobject = f.next()
    if tarobject.name == os.path.basename(path):
        return f.extractfile(tarobject).read()


###############################################################################


def run_masscan(target_ip) -> bytes:
    """Run Masscan in Docker."""
    client = docker.from_env()

    # Scan according to arguments.
    port_range = os.getenv("PORTS", "53,80,443")
    max_rate = os.getenv("MAX_RATE", 100)
    logging.info("Starting container %s to run masscan...", IMAGE)
    res = client.containers.run(
        image=IMAGE,
        command=f"-p {port_range} --max-rate {max_rate} -oJ {FILE_PATH} {target_ip}",
        detach=True,
    )
    res.wait()
    logging.debug(res.logs())

    output = get_file_from_container(container=res, path=FILE_PATH)

    # Do not crash the boefje if the output is known, instead log a warning.
    try:
        res.remove()
    except Exception as e:
        logging.warning(e)

    return output


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    """Creates webpage and takes capture using Playwright container."""
    input_ = boefje_meta.arguments["input"]
    ip_range = f"{input_['start_ip']['address']}/{str(input_['mask'])}"
    m_run = run_masscan(target_ip=ip_range)
    logging.info("Received a response with length %d", len(m_run))

    return [(set(), m_run)]
