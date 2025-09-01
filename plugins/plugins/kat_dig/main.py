import json
import os
import sys

import httpx


def run(file_id: str):
    headers = {"Authorization": "Token " + os.getenv("OPENKAT_TOKEN")}
    dig_file = httpx.get(f'{os.getenv("OPENKAT_API")}/file/{file_id}/', headers=headers).json()
    file = httpx.get(dig_file["file"], headers=headers)

    lines = [
        [part for part in line.split("\t") if part]
        for line in file.content.decode().split("\n")
        if not line.startswith(";") and line
    ]

    if not lines:
        return

    hostnames = set()

    oois = []
    for line in lines:
        try:
            hostname, ttl, record_class, record_type, content = line
        except ValueError:
            raise ValueError(f"Cannot parse line: {line}")

        hostnames.add(hostname.rstrip("."))

        oois.append(
            {
                "object_type": "DNSRecord",
                "hostname": f"Hostname|internet|{hostname}",
                "ttl": int(ttl),
                "dns_record_type": record_type,
                "value": content,
            }
        )

    oois.append(hostnames.pop())

    return oois


if __name__ == "__main__":
    oois = run(sys.argv[1])
    print(json.dumps(oois))
