import json
import os
import sys

import httpx


def run(file_id: str):
    token = os.getenv("OPENKAT_TOKEN")
    if not token:
        raise Exception("No OPENKAT_TOKEN env variable")

    base_url = os.getenv("OPENKAT_API")
    if not base_url:
        raise Exception("No OPENKAT_API env variable")

    headers = {"Authorization": "Token " + token}
    client = httpx.Client(base_url=base_url, headers=headers)
    drill_file = client.get(f"/file/{file_id}/").json()
    file_content = client.get(drill_file["file"]).content.decode()

    # Find the last status line (not just the last non-comment line)
    for result_line in reversed(file_content.splitlines()):
        if result_line.startswith(("[U]", "[S]", "[B]", "[T]")):
            domain = result_line.split("\t")[0].split(" ")[1].rstrip(".")
            break
    else:
        raise ValueError("No status line found in drill output")

    results = []

    # [S] self sig OK; [B] bogus; [T] trusted; [U] unsigned
    if result_line.startswith("[U]"):
        finding_type = {"object_type": "KATFindingType", "id": "KAT-NO-DNSSEC"}
        finding = {
            "object_type": "Finding",
            "ooi": f"Hostname|internet|{domain}",
            "finding_type": f"KATFindingType|{finding_type['id']}",
            "description": f"Domain {domain} is not signed with DNSSEC.",
        }
        results.extend([finding_type, finding])
    elif result_line.startswith("[S]") or result_line.startswith("[B]"):
        finding_type = {"object_type": "KATFindingType", "id": "KAT-INVALID-DNSSEC"}
        finding = {
            "object_type": "Finding",
            "ooi": f"Hostname|internet|{domain}",
            "finding_type": f"KATFindingType|{finding_type['id']}",
            "description": f"Domain {domain} is signed with an invalid DNSSEC.",
        }
        results.extend([finding_type, finding])

    client.post("/objects/", json=results)

    return results


if __name__ == "__main__":
    result = run(sys.argv[1])
    print(json.dumps(result))  # noqa: T201
