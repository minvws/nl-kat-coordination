import json
import sys
from base64 import b64encode

from main import run


def main():
    boefje_input = json.load(sys.stdin)
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

    json.dump(out, sys.stdout)


if __name__ == "__main__":
    main()
