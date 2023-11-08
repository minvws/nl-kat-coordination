import csv
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests

OCTOPOES_API = "http://localhost:8001"
KATALOGUS_API = "http://localhost:8003"
SCHEDULER_API = "http://localhost:8004"


def run():
    # Create organisations
    orgs: List[Dict[str, Any]] = []
    for n in range(1, 10):
        org = {
            "id": f"org-{n}",
            "name": f"Organisation {n}",
        }
        orgs.append(org)

        resp_katalogus = requests.post(
            url=f"{KATALOGUS_API}/v1/organisations/",
            json=org,
        )

        try:
            resp_katalogus.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if resp_katalogus.status_code != 404:
                print("Error creating organisation ", org)
                raise e

            if resp_katalogus.status_code == 404:
                print("Organisation already exists in katalogus", org)

        try:
            requests.post(
                url=f"{OCTOPOES_API}/{org.get('id')}/node/",
            )
        except requests.exceptions.HTTPError as e:
            print("Error creating organisation ", org)
            raise e

        print("Created organisation ", org)

        # Enable boefjes for organisation
        boefjes = ["dns-records", "dns-sec", "dns-zone"]
        for boefje_id in boefjes:
            resp_enable_boefje = requests.patch(
                url=f"{KATALOGUS_API}/v1/organisations/{org.get('id')}/repositories/LOCAL/plugins/{boefje_id}",
                json={"enabled": True},
            )

            try:
                resp_enable_boefje.raise_for_status()
            except requests.exceptions.HTTPError as e:
                print("Error enabling boefje ", boefje_id)
                raise e

            print("Enabled boefje ", boefje_id)

    declarations: List[Dict[str, Any]] = []
    with Path("data.csv").open(newline="") as csv_file:
        csv_reader = csv.DictReader(csv_file, delimiter=",", quotechar='"')
        for row in csv_reader:
            name = row["name"]
            decl = {
                "ooi": {
                    "object_type": "Hostname",
                    "primary_key": f"Hostname|internet|{name}",
                    "network": "Network|internet",
                    "name": f"{name}",
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
            declarations.append(decl)

    for org in orgs:
        for declaration in declarations:
            resp_octopoes_decl = requests.post(f"{OCTOPOES_API}/{org.get('id')}/declarations", json=declaration)

            try:
                resp_octopoes_decl.raise_for_status()
            except requests.exceptions.HTTPError as e:
                print("Error creating declaration ", declaration)
                print(resp_octopoes_decl.text)
                raise e

            print(f"Org {org.get('id')} created declaration ", declaration)

            resp_octopoes_scan_profile = requests.put(
                url=f"{OCTOPOES_API}/{org.get('id')}/scan_profiles",
                params={"valid_time": datetime.now(timezone.utc)},
                json={
                    "scan_profile_type": "declared",
                    "reference": declaration.get("ooi").get("scan_profile").get("reference"),
                    "level": declaration.get("ooi").get("scan_profile").get("level"),
                },
            )

            try:
                resp_octopoes_scan_profile.raise_for_status()
            except requests.exceptions.HTTPError as e:
                print("Error creating scan profile ", declaration.get("ooi").get("scan_profile"))
                print(resp_octopoes_scan_profile.text)
                raise e

            print(f"Org {org.get('id')} created scan profile ", declaration.get("ooi").get("scan_profile"))


if __name__ == "__main__":
    run()
