import json
import os
import sys
from collections import defaultdict

import httpx


def run(file_id: str) -> dict[str, list] | None:
    token = os.getenv("OPENKAT_TOKEN")
    if not token:
        raise Exception("No OPENKAT_TOKEN env variable")

    base_url = os.getenv("OPENKAT_API")
    if not base_url:
        raise Exception("No OPENKAT_API env variable")

    headers = {"Authorization": "Token " + token}
    client = httpx.Client(base_url=base_url, headers=headers)

    nuclei_output_file = client.get(f"/file/{file_id}/").json()
    file = client.get(nuclei_output_file["file"])

    results_grouped = defaultdict(list)

    for line in file.content.decode().split("\n"):
        if not line.strip():
            continue

        info = json.loads(line.strip())

        if info["template-id"].endswith("-detect"):
            software = info["template-id"].rstrip("-detect")
            results_grouped["ipaddress"].append({"address": info["ip"], "network": "internet"})
            results_grouped["ipport"].append(
                {
                    "address": info["ip"],
                    "protocol": info["type"].upper(),
                    "port": int(info["port"]),
                    "service": software,
                    "software": [{"name": software}],
                }
            )

    if not results_grouped["ipaddress"]:
        return None

    client.post("/objects/", headers=headers, json=results_grouped).json()

    return results_grouped


if __name__ == "__main__":
    results = run(sys.argv[1])

    print(json.dumps(results))  # noqa: T201
