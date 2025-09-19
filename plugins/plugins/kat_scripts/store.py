import argparse
import json
import os
import sys

import httpx


def findings() -> list[dict]:
    results = []
    for line in sys.stdin.readlines():
        finding_type_id, ooi = line.strip().split("\t", maxsplit=1)

        finding_type = {"object_type": "KATFindingType", "id": finding_type_id}
        finding = {"object_type": "Finding", "ooi": ooi, "finding_type": f"KATFindingType|{finding_type['id']}"}

        results.extend([finding_type, finding])

    return results


def hostnames() -> list[dict]:
    return [
        {"object_type": "Hostname", "name": l.strip(), "network": "Network|internet"} for l in sys.stdin.readlines()
    ]


if __name__ == "__main__":
    """ expects sys.stdin to have a newline separated list of finding_type_ids and ooi pks, separated by a tab """
    parser = argparse.ArgumentParser(description="Optional app description", add_help=False)
    parser.add_argument("-f", "--findings", action="store_true")
    parser.add_argument("-h", "--hostnames", action="store_true")
    args = parser.parse_args()

    if args.findings:
        results = findings()
    elif args.hostnames:
        results = hostnames()
    else:
        raise ValueError("No target type defined")

    if os.getenv("UPLOAD_URL") != "/dev/null":
        headers = {"Authorization": "Token " + os.getenv("OPENKAT_TOKEN")}
        httpx.post(f'{os.getenv("OPENKAT_API")}/objects/', headers=headers, json=results)

    json.dump(results, sys.stdout)  # stores the result as a JSON file as well
