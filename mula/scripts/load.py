import argparse
import csv
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

OCTOPOES_API = "http://localhost:8001"
KATALOGUS_API = "http://localhost:8003"
SCHEDULER_API = "http://localhost:8004"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

octopoes_client = httpx.Client(base_url=OCTOPOES_API)
katalogus_client = httpx.Client(base_url=KATALOGUS_API)
scheduler_client = httpx.Client(base_url=SCHEDULER_API)


def run(org_num: int = 1):
    # Create organisations
    orgs: list[dict[str, Any]] = []
    for n in range(0, org_num):
        org = {
            "id": f"org-{n}",
            "name": f"Organisation {n}",
        }
        orgs.append(org)

        resp_katalogus = katalogus_client.post(
            url="/v1/organisations/",
            json=org,
            timeout=30,
        )

        try:
            resp_katalogus.raise_for_status()
        except httpx.HTTPStatusError:
            if resp_katalogus.status_code != httpx.codes.NOT_FOUND:
                logger.info("Error creating organisation in katalogus %s", org)

            if resp_katalogus.status_code == httpx.codes.NOT_FOUND:
                logger.info("Organisation already exists in katalogus %s", org)

        resp_octo = octopoes_client.post(
            url=f"/{org.get('id')}/node",
            timeout=30,
        )

        try:
            resp_octo.raise_for_status()
        except httpx.HTTPStatusError:
            if resp_octo.status_code != httpx.codes.NOT_FOUND:
                logger.info("Error creating organisation in octopoes %s", org)

            if resp_octo.status_code == httpx.codes.NOT_FOUND:
                logger.info("Organisation already exists in octopoes %s", org)

            logger.info(resp_octo.content)

        logger.info("Created organisation %s", org)

        # Enable boefjes for organisation
        boefjes = ("dns-records", "dns-sec", "dns-zone")
        for boefje_id in boefjes:
            resp_enable_boefje = katalogus_client.patch(
                url=f"/v1/organisations/{org.get('id')}/plugins/{boefje_id}",
                json={"enabled": True},
                timeout=30,
            )

            try:
                resp_enable_boefje.raise_for_status()
            except httpx.HTTPError:
                logger.info("Error enabling boefje %s", boefje_id)
                raise

            logger.info("Enabled boefje %s", boefje_id)

    declarations: list[dict[str, Any]] = []

    # Check if data file exists
    if not Path("data.csv").exists():
        logger.info("data.csv file not found")
        return

    with Path("data.csv").open(newline="", encoding="utf-8") as csv_file:
        csv_reader = csv.DictReader(csv_file, delimiter=",", quotechar='"')
        for row in csv_reader:
            name = row["name"]
            declaration = {
                "ooi": {
                    "object_type": "Hostname",
                    "primary_key": f"Hostname|internet|{name}",
                    "network": "Network|internet",
                    "name": f"{name}",
                    "registered_domain": None,
                    "dns_zone": None,
                    "scan_profile": {
                        "scan_profile_type": "declared",
                        "level": 1,
                        "reference": f"Hostname|internet|{name}",
                    },
                },
                "valid_time": datetime.now(timezone.utc).isoformat(),
                "method": None,
                "task_id": str(uuid.uuid4()),
            }
            declarations.append(declaration)

    for org in orgs:
        for declaration in declarations[:10]:
            resp_octopoes_decl = octopoes_client.post(
                f"/{org.get('id')}/declarations",
                json=declaration,
                timeout=30,
            )

            try:
                resp_octopoes_decl.raise_for_status()
            except httpx.HTTPError:
                logger.info("Error creating declaration %s", declaration)
                logger.info(resp_octopoes_decl.text)
                raise

            logger.info("Org %s created declaration %s", org.get("id"), declaration)

            resp_octopoes_scan_profile = octopoes_client.put(
                url=f"/{org.get('id')}/scan_profiles",
                params={"valid_time": str(datetime.now(timezone.utc))},
                json={
                    "scan_profile_type": "declared",
                    "reference": declaration.get("ooi")
                    .get("scan_profile")
                    .get("reference"),
                    "level": declaration.get("ooi").get("scan_profile").get("level"),
                },
                timeout=30,
            )

            try:
                resp_octopoes_scan_profile.raise_for_status()
            except httpx.HTTPError:
                logger.info(
                    "Error creating scan profile %s",
                    declaration.get("ooi").get("scan_profile"),
                )
                logger.info(resp_octopoes_scan_profile.text)
                raise

            logger.info(
                "Org %s created scan profile %s",
                org.get("id"),
                declaration.get("ooi").get("scan_profile"),
            )


if __name__ == "__main__":
    # Setup command line interface
    parser = argparse.ArgumentParser(description="Load test the scheduler")

    # Add arguments
    parser.add_argument(
        "--orgs", type=int, default=1, help="Number of organisations to create"
    )

    # Parse arguments
    args = parser.parse_args()

    run(org_num=args.orgs)
