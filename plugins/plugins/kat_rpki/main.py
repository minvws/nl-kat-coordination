# /// script
# dependencies = [
#   "httpx==0.27.2",
#   "polars==1.32.3",
#   "polars-iptools==0.1.10",
# ]
# ///

import json
from json import JSONDecodeError
from os import getenv

import httpx
import polars as pl
import polars_iptools as ip


def run():
    client = httpx.Client(base_url=getenv("OPENKAT_API"), headers={"Authorization": "Token " + getenv("OPENKAT_TOKEN")})
    rpki_lazy = download_lazyframe(client, "rpki-download")
    bgp_lazy = download_lazyframe(client, "bgp-download")

    ip4s = get_all_objects_of_type(client, "IPAddressV4")
    ip6s = get_all_objects_of_type(client, "IPAddressV6")  # TODO

    rpki_filtered_v4 = rpki_lazy.filter(pl.col("prefix").str.contains(".", literal=True)).with_columns(
        intip=ip.ipv4_to_numeric(pl.col("prefix").str.split("/").list.get(0)),  # parse CIDR to start ip as integer
        intprefix=pl.col("prefix").str.split("/").list.get(1).cast(pl.UInt8),   # parse prefix to integer
    )
    bgp_filtered_v4 = bgp_lazy.filter(pl.col("CIDR").str.contains(".", literal=True)).with_columns(
        bintip=ip.ipv4_to_numeric(pl.col("CIDR").str.split("/").list.get(0)),  # parse CIDR to start ip as integer
        bintprefix=pl.col("CIDR").str.split("/").list.get(1).cast(pl.UInt8),   # parse prefix to integer
    )

    ip4s_lazy = pl.LazyFrame({"ip": [x["address"] for x in ip4s.values()]}).with_columns(intip4=ip.ipv4_to_numeric("ip"))
    new = ip4s_lazy.join_where(
        rpki_filtered_v4,
        pl.col("intip") <= pl.col("intip4"),
        pl.col("intip") + 2 ** (32 - pl.col("intprefix")) >= pl.col("intip4"),
    )
    bgp_new = set(new.join_where(
        bgp_filtered_v4,
        pl.col("bintip") <= pl.col("intip4"),
        pl.col("bintip") + 2 ** (32 - pl.col("bintprefix")) >= pl.col("intip4"),
        pl.col("asn") != pl.col("ASN"),
    ).select("ip").collect()["ip"].unique())

    results = []

    ip4s_with_rpki = set(new.select("ip").collect()["ip"].unique())

    for pk, ip4 in ip4s.items():
        if ip4["address"] not in ip4s_with_rpki:
            ft = dict(object_type="KATFindingType", id="KAT-NO-RPKI")
            f = dict(object_type="Finding", finding_type=f"KATFindingType|{ft['id']}", ooi=pk)
            results.extend([ft, f])
            continue

        if ip4["address"] in bgp_new:
            ft = dict(object_type="KATFindingType", id="KAT-INVALID-RPKI")
            f = dict(object_type="Finding", finding_type=f"KATFindingType|{ft['id']}", ooi=pk)
            results.extend([ft, f])

    client.post('/objects/', json=results)

    return results


def download_lazyframe(client, file_type: str) -> pl.LazyFrame:
    params = {"ordering": "created_at", "limit": 1}

    try:
        file = client.get("/file/", params=params | {"search": file_type}).json()["results"][0]["file"]
    except (IndexError, JSONDecodeError):
        raise FileNotFoundError(f"No {file_type} found. Please enable the download plugin first.")

    rpki_lazy = pl.scan_parquet(client.get(file).content)

    return rpki_lazy


def get_all_objects_of_type(client: httpx.Client, object_type: str) -> dict[str, dict]:
    offset = 0
    limit = 500
    results = {}

    while True:
        new = client.get("/objects/", params={"object_type": object_type, "offset": offset, "limit": limit}).json()

        if not new["results"]:
            break

        for result in new["results"]:
            results[result["primary_key"]] = result

        if len(new["results"]) < limit:
            break

        offset += limit

    return results


if __name__ == "__main__":
    oois = run()
    print(json.dumps(oois))
