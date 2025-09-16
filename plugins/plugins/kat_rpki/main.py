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


def run():
    client = httpx.Client(base_url=getenv("OPENKAT_API"), headers={"Authorization": "Token " + getenv("OPENKAT_TOKEN")})
    rpki = download_lazyframe(client, "rpki-download")
    bgp = download_lazyframe(client, "bgp-download")

    ip4s = get_all_objects_of_type(client, "IPAddressV4")
    ip6s = get_all_objects_of_type(client, "IPAddressV6")  # TODO

    rpki_v4 = rpki.filter(pl.col("prefix").str.contains(".", literal=True)).with_columns(  # filter ipv4 addresses
        intip=ip.ipv4_to_numeric(pl.col("prefix").str.split("/").list.get(0)),  # parse CIDR to start-ip as an integer
        intprefix=pl.col("prefix").str.split("/").list.get(1).cast(pl.UInt8),   # parse CIDR to prefix as an integer
    )
    rpki_v6 = rpki.filter(pl.col("prefix").str.contains(":", literal=True)).with_columns(  # filter ipv4 addresses
        intip=pl.col("prefix").str.split("/").list.get(0).map_elements(ipv6_to_int, return_dtype=pl.Int128),  # parse CIDR to start-ip as an integer
        intprefix=pl.col("prefix").str.split("/").list.get(1).cast(pl.UInt8),   # parse CIDR to prefix as an integer
    )

    bgp_v4 = bgp.filter(pl.col("CIDR").str.contains(".", literal=True)).with_columns(  # filter ipv4 addresses
        bintip=ip.ipv4_to_numeric(pl.col("CIDR").str.split("/").list.get(0)),  # parse CIDR to start-ip as an integer
        bintprefix=pl.col("CIDR").str.split("/").list.get(1).cast(pl.UInt8),   # parse CIDR to prefix as an integer
    )
    bgp_v6 = bgp.filter(pl.col("CIDR").str.contains(":", literal=True)).with_columns(  # filter ipv4 addresses
        bintip=pl.col("CIDR").str.split("/").list.get(0).map_elements(ipv6_to_int, return_dtype=pl.Int128),  # parse CIDR to start-ip as an integer
        bintprefix=pl.col("CIDR").str.split("/").list.get(1).cast(pl.UInt8),   # parse CIDR to prefix as an integer
    )

    # Create a pl.LazyFrame out of the object list of IPAddresses
    ip4s_lazy = pl.LazyFrame(
        {"ip": [x["address"] for x in ip4s.values()]}).with_columns(intip4=ip.ipv4_to_numeric("ip")
    )
    ip6s_lazy = pl.LazyFrame({"ip": [x["address"] for x in ip6s.values()]}).with_columns(
        intip6=pl.col("ip").map_elements(ipv6_to_int, return_dtype=pl.Int128)
    )
    # Based on the start-ip and prefix, calculate if an ip from ip4s_lazy is within the range of a row from rpki_v4.
    # Create a new LazyFrame where an ip address is matched to any rpki_v4 with a network containing the ip.
    pl2 = pl.lit(2, dtype=pl.Int128)
    new_v4 = ip4s_lazy.join_where(
        rpki_v4,
        pl.col("intip") <= pl.col("intip4"),
        pl.col("intip") >= pl.col("intip4") - pl2 ** (32 - pl.col("intprefix")) + 1,
    )

    new_v6 = ip6s_lazy.join_where(
        rpki_v6,
        pl.col("intip") <= pl.col("intip6"),
        pl.col("intip") >= pl.col("intip6") - pl2 ** 100,
    )

    # Join the bgp data the same way, creating a dataframe with all possible triplets (rpki_network, bgp_network, ip)
    # where "ip in rpki_network && ip in bgp_network". (In general, the list of ip addresses is relatively small and
    # this results in a dataframe with roughly 5-10 rows per ip address.)
    bgp_new_v4 = set(new_v4.join_where(
        bgp_v4,
        pl.col("bintip") <= pl.col("intip4"),
        pl.col("bintip") + pl2 ** (32 - pl.col("bintprefix")) >= pl.col("intip4"),
        pl.col("asn") != pl.col("ASN"),
    ).select("ip").collect()["ip"].unique())

    bgp_new_v6 = set(new_v6.join_where(
        bgp_v6,
        pl.col("bintip") <= pl.col("intip6"),
        pl.col("bintip") + pl2 ** (128 - pl.col("bintprefix")) >= pl.col("intip6"),
        pl.col("asn") != pl.col("ASN"),
    ).select("ip").collect()["ip"].unique())

    results = []

    ip4s_with_rpki = set(new_v4.select("ip").collect()["ip"].unique())
    ip6s_with_rpki = set(new_v6.select("ip").collect()["ip"].unique())

    for pk, ip_ooi in (ip4s | ip6s).items():
        if ip_ooi["address"] not in ip4s_with_rpki and ip_ooi["address"] not in ip6s_with_rpki:
            ft = dict(object_type="KATFindingType", id="KAT-NO-RPKI")
            f = dict(object_type="Finding", finding_type=f"KATFindingType|{ft['id']}", ooi=pk)
            results.extend([ft, f])
            continue

        if ip_ooi["address"] in bgp_new_v4 or ip_ooi["address"] in bgp_new_v6:
            ft = dict(object_type="KATFindingType", id="KAT-INVALID-RPKI")
            f = dict(object_type="Finding", finding_type=f"KATFindingType|{ft['id']}", ooi=pk)
            results.extend([ft, f])

    client.post('/objects/', json=results)

    return results


def download_lazyframe(client, file_type: str) -> pl.LazyFrame:
    """ Download the most recent version of a parquet file with type file_type and read this into a pl.LazyFrame """

    params = {"ordering": "created_at", "limit": 1}

    try:
        file = client.get("/file/", params=params | {"search": file_type}).json()["results"][0]["file"]
    except (IndexError, JSONDecodeError):
        raise FileNotFoundError(f"No {file_type} found. Please enable the download plugin first.")

    rpki_lazy = pl.scan_parquet(client.get(file).content)

    return rpki_lazy


def get_all_objects_of_type(client: httpx.Client, object_type: str) -> dict[str, dict]:
    """ Iterate through the object API to collect all objects of type object_type """

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
