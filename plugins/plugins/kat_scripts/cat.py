import os
import sys

import httpx


def main(file_id: str):
    headers = {"Authorization": "Token " + os.getenv("OPENKAT_TOKEN")}
    client = httpx.Client(base_url=os.getenv("OPENKAT_API"), headers=headers)

    file_meta = client.get(f'/file/{file_id}/').json()
    file = client.get(file_meta["file"])
    sys.stdout.write(file.read().decode())


if __name__ == "__main__":
    main(sys.argv[1])
