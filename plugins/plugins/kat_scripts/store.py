import argparse
import json
import os
import sys

import httpx


def findings(object_type: str) -> list[dict]:
    results = []
    for line in sys.stdin.readlines():
        code, obj = line.strip().split("\t", maxsplit=1)
        results.append({"finding_type_code": code, "object_code": obj.strip(), "object_type": object_type})

    return results


def hostnames() -> list[dict]:
    return [{"name": line.strip(), "network": "internet"} for line in sys.stdin.readlines()]


if __name__ == "__main__":
    """ expects sys.stdin to have a newline separated list of finding_type_ids and object pks, separated by a tab """
    parser = argparse.ArgumentParser(description="Optional app description", add_help=False)
    parser.add_argument("-f", "--findings", action="store_true")
    parser.add_argument("-t", "--object_type")
    parser.add_argument("-h", "--hostnames", action="store_true")
    args = parser.parse_args()

    token = os.getenv("OPENKAT_TOKEN")

    if not token:
        raise Exception("No OPENKAT_TOKEN env variable")

    headers = {"Authorization": "Token " + token}

    if args.findings:
        results = findings(args.object_type)
        httpx.post(f"{os.getenv('OPENKAT_API')}/objects/finding/", headers=headers, json=results, timeout=30)
    elif args.hostnames:
        results = hostnames()
        httpx.post(f"{os.getenv('OPENKAT_API')}/objects/hostname/", headers=headers, json=results, timeout=30)
    else:
        raise ValueError("No target type defined")

    json.dump(results, sys.stdout)  # stores the result as a JSON file as well
