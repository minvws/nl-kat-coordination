import os
import sys
import traceback
from base64 import b64encode

import httpx
from main import run


def main():
    input_url = sys.argv[-1]
    try:
        response = httpx.get(input_url)
        response.raise_for_status()
        boefje_input = response.json()
    except httpx.HTTPError as e:
        # sys.exit will print the message on stderr and return with exit code 1
        sys.exit(f"Failed to get input from boefje API: {e}")

    try:
        os.environ.update(boefje_input["boefje_meta"]["environment"])
        raws = run(boefje_input["boefje_meta"])
        out = {
            "status": "COMPLETED",
            "files": [
                {
                    "content": (b64encode(x[1]) if isinstance(x[1], bytes) else b64encode(x[1].encode())).decode(),
                    "tags": list(x[0]),
                }
                for x in raws
            ],
        }
    except Exception:
        out = {
            "status": "FAILED",
            "files": [
                {"name": None, "content": b64encode(traceback.format_exc().encode()).decode(), "tags": ["error/boefje"]}
            ],
        }

    try:
        response = httpx.post(boefje_input["output_url"], json=out)
        response.raise_for_status()
    except httpx.HTTPError as e:
        sys.exit(f"Failed to post output to boefje API: {e}")


if __name__ == "__main__":
    main()
