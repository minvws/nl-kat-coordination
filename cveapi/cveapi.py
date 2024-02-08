#!/usr/bin/env python3

import json
import logging
import os
import pathlib
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import requests

logger = logging.getLogger("cveapi")


def download_files(directory, last_update, update_timestamp):
    index = 0
    session = requests.Session()
    error_count = 0

    while True:
        if last_update:
            parameters = f"startIndex={index}&lastModStartDate={quote(last_update.isoformat())}"
            parameters += f"&lastModEndDate={quote(update_timestamp.isoformat())}"
        else:
            parameters = f"startIndex={index}"
        logger.debug("Parameters are %s", parameters)

        r = session.get(f"https://services.nvd.nist.gov/rest/json/cves/2.0/?{(parameters)}", timeout=60)
        if r.status_code != 200:
            error_count += 1
            if error_count == 5:
                logger.error("Got 5 errors when trying to download data, giving up")
                r.raise_for_status()
            logger.debug("Error fetching data, sleeping 10 seconds and trying again")
            time.sleep(10)
            continue

        # Reset error count
        error_count = 0

        response_json = r.json()

        logger.debug("Fetched %d of %d results", response_json["resultsPerPage"], response_json["totalResults"])

        for cve in response_json["vulnerabilities"]:
            filename = directory / f"{cve['cve']['id']}.json"
            with filename.open("w") as f:
                json.dump(cve, f)
            last_modified = datetime.fromisoformat(cve["cve"]["lastModified"]).timestamp()
            os.utime(filename, (last_modified, last_modified))

        if response_json["startIndex"] + response_json["resultsPerPage"] == response_json["totalResults"]:
            break

        index += response_json["resultsPerPage"]

        # Ratelimit without API key is 5 requests per 30 seconds
        time.sleep(30 / 5)

    logger.info("Downloaded new information of %s CVEs", response_json["totalResults"])


def run():
    loglevel = os.getenv("CVEAPI_LOGLEVEL", "INFO")
    numeric_level = getattr(logging, loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError("Invalid log level: %s" % loglevel)
    logging.basicConfig(format="%(message)s", level=numeric_level)

    cveapi_dir = os.getenv("CVEAPI_DIR", "/var/lib/kat-cveapi")
    directory = pathlib.Path(cveapi_dir) / "v1"
    directory.mkdir(parents=True, exist_ok=True)

    last_update_filename = directory / "lastupdate.json"
    last_update = None
    if last_update_filename.exists():
        with last_update_filename.open() as f:
            last_update = datetime.fromisoformat(json.load(f)["last_update"])
        logger.info("Last update was %s", last_update.astimezone())

    update_timestamp = datetime.now(timezone.utc)
    update_timestamp = update_timestamp.replace(microsecond=0)

    if last_update and update_timestamp - last_update > timedelta(days=120):
        # The NVD API allows a maximum 120 day interval. If this is run when the
        # last update is longer than 120 days we will just download everything
        # again.
        last_update = None

    download_files(directory, last_update, update_timestamp)

    with last_update_filename.open("w") as f:
        json.dump({"last_update": update_timestamp.isoformat()}, f)
