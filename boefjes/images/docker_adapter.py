import sys
from base64 import b64encode

import httpx
from main import run


def main():
    input_url = sys.argv[-1]
    boefje_input = httpx.get(input_url).json()

    raws = run(boefje_input["boefje_meta"])
    out = {
        "status": "COMPLETED",
        "files": [
            {
                "name": None,
                "content": (b64encode(x[1]) if isinstance(x[1], bytes) else b64encode(x[1].encode())).decode(),
                "tags": list(x[0]),
            }
            for x in raws
        ],
    }
    httpx.post(boefje_input["output_url"], data=out)


if __name__ == "__main__":
    main()
