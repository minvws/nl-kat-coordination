import io
import logging
import os
import tarfile
from typing import ByteString, Generator, List, Tuple, Union

import docker
from PIL import Image

from boefjes.job_models import BoefjeMeta

PLAYWRIGHT_IMAGE = "mcr.microsoft.com/playwright:v1.33.0-jammy"
BROWSER = "chromium"


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


def get_file_from_container(container: docker.models.containers.Container, path: str) -> bytes:
    """Returns a file from a docker container."""
    try:
        stream, _ = container.get_archive(path)
    except docker.errors.NotFound:
        logging.warning(
            "[Webpage Capture] %s not found in container %s %s", path, container.short_id, container.image.tags
        )
        return None

    f = tarfile.open(mode="r|", fileobj=TarStream(stream).reader())
    tarobject = f.next()
    if tarobject.name == os.path.basename(path):
        return f.extractfile(tarobject).read()


def build_playwright_command(webpage: str, browser: str, tmp_path: str) -> str:
    """Returns playwright command including webpage, browser and locations for image, har and storage."""
    return " ".join(
        [
            "npx playwright screenshot",
            f"-b {browser}",
            "--full-page",
            f"--save-har={tmp_path}.har.zip",
            f"--save-storage={tmp_path}.json",
            webpage,
            f"{tmp_path}.png",
        ]
    )


def run_playwright(webpage: str, browser: str, tmp_path: str = "/tmp/tmp") -> Tuple[bytes]:
    """Run Playwright in Docker."""
    client = docker.from_env()
    res = client.containers.run(
        image=PLAYWRIGHT_IMAGE,
        command=[
            "/bin/sh",
            "-c",
            f"npx -y {build_playwright_command(webpage=webpage, browser=browser, tmp_path=tmp_path)}",
        ],
        detach=True,
    )
    try:
        res.wait()
        image = Image.open(io.BytesIO(get_file_from_container(container=res, path=f"{tmp_path}.png")))
        har = get_file_from_container(container=res, path=f"{tmp_path}.har.zip")
        storage = get_file_from_container(container=res, path=f"{tmp_path}.json")
    finally:
        res.remove()

    return image.tobytes(), har, storage


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    """Creates webpage and takes capture using Playwright container."""
    input_ = boefje_meta.arguments["input"]
    webpage = f"{input_['scheme']}://{input_['netloc']['name']}{input_['path']}"

    image_bytes, har_zip, storage_json = run_playwright(webpage=webpage, browser=BROWSER)

    return [
        (set("image/png"), image_bytes),
        (set("application/zip+json"), har_zip),
        (set("application/json"), storage_json),
    ]
