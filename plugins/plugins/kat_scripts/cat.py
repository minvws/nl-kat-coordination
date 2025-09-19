import os
import sys

import httpx


def main(file_id: str):
    token = os.getenv("OPENKAT_TOKEN")
    if not token:
        raise Exception("No OPENKAT_TOKEN env variable")

    base_url = os.getenv("OPENKAT_API")
    if not base_url:
        raise Exception("No OPENKAT_API env variable")

    headers = {"Authorization": "Token " + token}
    client = httpx.Client(base_url=base_url, headers=headers)

    file_meta = client.get(f"/file/{file_id}/").json()
    file = client.get(file_meta["file"])
    sys.stdout.write(file.read().decode())


if __name__ == "__main__":
    main(sys.argv[1])
