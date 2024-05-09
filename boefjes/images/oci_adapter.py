import os
import sys
import traceback
from base64 import b64encode

import httpx
from main import run


def main():
    input_url = sys.argv[-1]
    boefje_input = httpx.get(input_url).json()

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

    httpx.post(boefje_input["output_url"], json=out)


if __name__ == "__main__":
    main()
