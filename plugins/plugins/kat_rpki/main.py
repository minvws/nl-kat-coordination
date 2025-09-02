# /// script
# dependencies = [
#   "httpx",
#   "polars",
# ]
# ///

import json
import os
import sys
from json import JSONDecodeError

import httpx
import polars as pl


def run(rpki_file_id, bgp_file_id):
    headers = {"Authorization": "Token " + os.getenv("OPENKAT_TOKEN")}
    client = httpx.Client(base_url=os.getenv("OPENKAT_API"), headers=headers)

    try:
        rpki_file = client.get(
            "/file/", params={"ordering": "created_at", "limit": 1, "search": "rpki-download"}
        ).json()["results"][0]["file"]
    except (IndexError, JSONDecodeError):
        raise FileNotFoundError("No RPKI file found. Please enable the rpki-download and bgp-download plugins first.")

    try:
        bgp_file = client.get("/file/", params={"ordering": "created_at", "limit": 1, "search": "bgp-download"}).json()[
            "results"
        ][0]["file"]
    except (IndexError, JSONDecodeError):
        raise FileNotFoundError("No BGP file found. Please enable the rpki-download and bgp-download plugins first.")

    rpki_lazy = pl.scan_parquet(client.get(rpki_file).content)
    bgp_lazy = pl.scan_parquet(client.get(bgp_file).content)

    # TODO: Match all ips against these dataframes

    # TODO: if the address is private, we do not need a ROA

    raise NotImplementedError

    results = []

    for ip in rpki_lazy:
        ft = dict(object_type="KATFindingType", id="KAT-NO-RPKI")
        f = dict(object_type="Finding", finding_type=ft, ooi=ip)
        results.extend([ft, f])

        ft = dict(object_type="KATFindingType", id="KAT-INVALID-RPKI")
        f = dict(object_type="Finding", finding_type=ft, ooi=ip)
        results.extend([ft, f])


if __name__ == "__main__":
    oois = run(sys.argv[1], sys.argv[2])
    print(json.dumps(oois))
