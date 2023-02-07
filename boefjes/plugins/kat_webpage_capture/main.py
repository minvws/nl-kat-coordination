from typing import Tuple, Union, List

from boefjes.job_models import BoefjeMeta
from PIL import Image
import io
import os
import docker
import logging
import tarfile

PLAYWRIGHT_IMAGE = "mcr.microsoft.com/playwright:v1.30.0-focal"
BROWSER = "chromium"


def get_file_from_container(container: docker.models.containers.Container, path: str) -> bytes:
    """Returns a file from a docker container."""
    try:
        stream, _ = container.get_archive(path)
    except docker.errors.NotFound:
        logging.warning(f"[Webpage Capture] {path} not found in container {container.short_id} {container.image.tags}")
        return None

    # Extract a file as archive stream and write to BytesIO.
    file_as_tar_bytes = io.BytesIO()
    for stream_part in stream:
        file_as_tar_bytes.write(stream_part)
    file_as_tar_bytes.seek(0)

    # Get the file from the tar object.
    return tarfile.open(mode="r", fileobj=file_as_tar_bytes).extractfile(os.path.basename(path)).read()


def build_playwright_command(webpage: str, browser: str, tmp_path: str) -> str:
    return " ".join(
        [
            "playwright screenshot",
            f"-b {browser}",
            "--full-page",
            f"--save-har={tmp_path}.har.zip",
            f"--save-storage={tmp_path}.json",
            webpage,
            f"{tmp_path}.png",
        ]
    )


def run_playwright(webpage: str, browser: str, tmp_path: str = "/tmp/tmp") -> List[bytes]:
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
    res.wait()
    logging.warning("[Webpage Capture] HAR (.har.zip) and Storage (.json) files not working in 1.30.0.")
    image = Image.open(io.BytesIO(get_file_from_container(container=res, path=f"{tmp_path}.png")))
    har = get_file_from_container(container=res, path=f"{tmp_path}.har.zip")
    storage = get_file_from_container(container=res, path=f"{tmp_path}.json")
    res.remove()

    return image.tobytes(), har, storage


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    """Creates webpage and takes capture using Playwright container."""
    input_ = boefje_meta.arguments["input"]
    webpage = f"{input_['scheme']}://{input_['netloc']['name']}{input_['path']}"

    image_bytes, har_zip, storage_json = run_playwright(webpage=webpage, browser=BROWSER)

    return [(set("image/bytes"), image_bytes), (set("har/zip"), har_zip), (set("webstorage/json"), storage_json)]
