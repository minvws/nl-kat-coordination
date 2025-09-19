# /// script
# dependencies = [
#   "httpx==0.27.2",
#   "polars==1.32.3",
#   "polars-iptools==0.1.10",
# ]
# ///

import json
import socket
from binascii import hexlify
from json import JSONDecodeError
from os import getenv

import httpx
import polars as pl
import polars_iptools as ip


def ipv6_to_int(ipv6_addr):
    return int(hexlify(socket.inet_pton(socket.AF_INET6, ipv6_addr)), 16)


def run(rpki: pl.LazyFrame, bgp: pl.LazyFrame, ip4s: dict[str, dict], ip6s: dict[str, dict]):
    rpki_v4 = rpki.filter(pl.col("prefix").str.contains(".", literal=True)).with_columns(  # filter ipv4 addresses
        intip=ip.ipv4_to_numeric(pl.col("prefix").str.split("/").list.get(0)),  # parse CIDR to start-ip as an integer
        intprefix=pl.col("prefix").str.split("/").list.get(1).cast(pl.UInt8),  # parse CIDR to prefix as an integer
    )
    rpki_v6 = rpki.filter(pl.col("prefix").str.contains(":", literal=True)).with_columns(
        intip=pl.col("prefix").str.split("/").list.get(0).map_elements(ipv6_to_int, return_dtype=pl.Int128),
        intprefix=pl.col("prefix").str.split("/").list.get(1).cast(pl.UInt8),
    )

    bgp_v4 = bgp.filter(pl.col("CIDR").str.contains(".", literal=True)).with_columns(
        bintip=ip.ipv4_to_numeric(pl.col("CIDR").str.split("/").list.get(0)),
        bintprefix=pl.col("CIDR").str.split("/").list.get(1).cast(pl.UInt8),
    )
    bgp_v6 = bgp.filter(pl.col("CIDR").str.contains(":", literal=True)).with_columns(
        bintip=pl.col("CIDR").str.split("/").list.get(0).map_elements(ipv6_to_int, return_dtype=pl.Int128),
        bintprefix=pl.col("CIDR").str.split("/").list.get(1).cast(pl.UInt8),
    )

    # Create a pl.LazyFrame out of the object list of IPAddresses
    ip4s_lazy = pl.LazyFrame(list(ip4s.values())).with_columns(intip4=ip.ipv4_to_numeric("address"))
    ip6s_lazy = pl.LazyFrame(list(ip6s.values())).with_columns(
        intip6=pl.col("address").map_elements(ipv6_to_int, return_dtype=pl.Int128)
    )

    # Based on the start-ip and prefix, calculate if an ip from ip4s_lazy is within the range of a row from rpki_v4.
    # Create a new LazyFrame where an ip address is matched to any rpki_v4 with a network containing the ip.
    pl2 = pl.lit(2, dtype=pl.Int128)
    new_v4 = ip4s_lazy.join_where(
        rpki_v4,
        pl.col("intip") <= pl.col("intip4"),
        pl.col("intip") >= pl.col("intip4") - pl2 ** (32 - pl.col("intprefix")) + 1,
    )
    bgp_new_v4 = ip4s_lazy.join_where(
        bgp_v4,
        pl.col("bintip") <= pl.col("intip4"),
        pl.col("bintip") + pl2 ** (32 - pl.col("bintprefix")) >= pl.col("intip4") + 1,
    )
    bgp_rpki_v4 = bgp_new_v4.join(new_v4, left_on=["address", "ASN"], right_on=["address", "asn"], how="left").filter(
        pl.col("primary_key_right").is_null()
    )

    new_v6 = ip6s_lazy.join_where(
        rpki_v6,
        pl.col("intip") <= pl.col("intip6"),
        pl.col("intip") >= pl.col("intip6") - pl2 ** (128 - pl.col("intprefix")) + 1,
    )
    bgp_new_v6 = ip6s_lazy.join_where(
        bgp_v6,
        pl.col("bintip") <= pl.col("intip6"),
        pl.col("bintip") >= pl.col("intip6") - pl2 ** (128 - pl.col("bintprefix")) + 1,
    )
    bgp_rpki_v6 = bgp_new_v6.join(new_v6, left_on=["address", "ASN"], right_on=["address", "asn"], how="left").filter(
        pl.col("primary_key_right").is_null()
    )

    results = []

    ip4s_without_rpki = ip4s_lazy.join(new_v4, on="address", how="left").filter(pl.col("prefix").is_null())
    ip6s_without_rpki = ip6s_lazy.join(new_v6, on="address", how="left").filter(pl.col("prefix").is_null())

    for pk, address in ip4s_without_rpki.select(["primary_key", "address"]).collect().iter_rows():
        ft = dict(object_type="KATFindingType", id="KAT-NO-RPKI")
        f = dict(object_type="Finding", finding_type=f"KATFindingType|{ft['id']}", ooi=pk)
        results.extend([ft, f])

    for pk, address in ip6s_without_rpki.select(["primary_key", "address"]).collect().iter_rows():
        ft = dict(object_type="KATFindingType", id="KAT-NO-RPKI")
        f = dict(object_type="Finding", finding_type=f"KATFindingType|{ft['id']}", ooi=pk)
        results.extend([ft, f])

    for pk, address in bgp_rpki_v4.select(["primary_key", "address"]).collect().iter_rows():
        ft = dict(object_type="KATFindingType", id="KAT-INVALID-RPKI")
        f = dict(object_type="Finding", finding_type=f"KATFindingType|{ft['id']}", ooi=pk)
        results.extend([ft, f])

    for pk, address in bgp_rpki_v6.select(["primary_key", "address"]).collect().iter_rows():
        ft = dict(object_type="KATFindingType", id="KAT-INVALID-RPKI")
        f = dict(object_type="Finding", finding_type=f"KATFindingType|{ft['id']}", ooi=pk)
        results.extend([ft, f])

    return results


def download_lazyframe(client, file_type: str) -> pl.LazyFrame:
    """Download the most recent version of a parquet file with type file_type and read this into a pl.LazyFrame"""

    params = {"ordering": "created_at", "limit": 1}

    try:
        file = client.get("/file/", params=params | {"search": file_type}).json()["results"][0]["file"]
    except (IndexError, JSONDecodeError):
        raise FileNotFoundError(f"No {file_type} found. Please enable the download plugin first.")

    rpki_lazy = pl.scan_parquet(client.get(file).content)

    return rpki_lazy


def get_all_objects_of_type(client: httpx.Client, object_type: str) -> dict[str, dict]:
    """Iterate through the object API to collect all objects of type object_type"""

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
    client = httpx.Client(base_url=getenv("OPENKAT_API"), headers={"Authorization": "Token " + getenv("OPENKAT_TOKEN")})
    oois = run(
        download_lazyframe(client, "rpki-download"),
        download_lazyframe(client, "bgp-download"),
        get_all_objects_of_type(client, "IPAddressV4"),
        get_all_objects_of_type(client, "IPAddressV6"),
    )

    client.post("/objects/", json=oois)

    print(json.dumps(oois))
