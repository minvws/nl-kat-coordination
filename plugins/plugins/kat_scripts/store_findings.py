import json
import os
import re
import sys

import httpx

CVE_PATTERN = re.compile(r"CVE-\d{4}-\d{4,}")


def main():
    results = []
    for line in sys.stdin.readlines():
        finding_type_id, ooi = line.strip().split("\t", maxsplit=1)

        finding_type = {"object_type": "KATFindingType", "id": finding_type_id}
        finding = {"object_type": "Finding", "ooi": ooi, "finding_type": f"KATFindingType|{finding_type['id']}"}

        results.extend([finding_type, finding])

    return results


if __name__ == "__main__":
    results = main()

    if os.getenv("UPLOAD_URL") != "/dev/null":
        headers = {"Authorization": "Token " + os.getenv("OPENKAT_TOKEN")}
        httpx.post(f'{os.getenv("OPENKAT_API")}/objects/', headers=headers, json=results)

    json.dump(results, sys.stdout)  # stores the result as a JSON file as well
