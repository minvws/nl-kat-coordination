import datetime
import hashlib
import json
import os
import re
from dataclasses import dataclass
from itertools import product
from typing import Optional, Tuple, List, Dict, Union

import requests
from ares import CVESearch
from bs4 import BeautifulSoup
from cwe import Database

from rocky.settings import BASE_DIR

RETIREJS_SOURCE = (
    "https://github.com/RetireJS/retire.js/blob/master/repository/jsrepository.json"
)

SEPARATOR = "|"


@dataclass
class _Service:
    name: str
    port: Optional[int] = None
    transport_protocol: Optional[str] = None
    description: Optional[str] = None


@dataclass
class _PortInfo:
    port: int
    protocols: list
    description: str


def cve_info(cve_id: str) -> dict:
    """Uses the ares module to find information on cves"""
    cve_search = CVESearch()
    cve_information = cve_search.id(cve_id)

    if cve_information:
        return {
            "description": cve_information.get("summary"),
            "cvss": cve_information.get("cvss"),
            "source": f"https://cve.circl.lu/cve/{cve_id}",
            "information updated": datetime.datetime.now().strftime(
                "%d-%m-%Y %H:%M:%S"
            ),
        }

    return {"description": "Not found"}


def snyk_info(snyk_id: str) -> dict:
    """Uses the ares module to find information on cves"""
    snyk_information = _snyk_search(snyk_id)

    if snyk_information:
        return {
            "description": snyk_information.get("summary"),
            "risk": snyk_information.get("risk"),
            "source": f"https://snyk.io/vuln/{snyk_id}",
            "affected versions": snyk_information.get("affected_versions"),
            "information updated": datetime.datetime.now().strftime(
                "%d-%m-%Y %H:%M:%S"
            ),
        }

    return {"description": "Not found"}


def _snyk_search(snyk_id: str) -> Dict:
    url_snyk = f"https://snyk.io/vuln/{snyk_id}"
    page = requests.get(url_snyk)
    soup = BeautifulSoup(page.content, "html.parser")
    return {
        "risk": soup.select("[data-snyk-test-score]")[0].attrs["data-snyk-test-score"],
        "affected_versions": soup.select("[data-snyk-test='vuln versions']")[
            0
        ].text.strip(),
        "summary": soup.findAll("h2", text=re.compile(r"Overview"))[0]
        .parent.text.strip()
        .split("\n")[2],
    }


def retirejs_info(retirejs_id: str) -> dict:
    """Uses the retirejs vulnerabilities list to find outdated javascript instances"""
    filename_path = os.path.join(BASE_DIR, "data/retirejs.json")
    with open(filename_path, encoding="utf-8") as json_file:
        data = json.load(json_file)

    _, name, hashed_id = retirejs_id.split("-")

    software = [
        brand
        for brand in data
        if name
        == brand.lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
        .replace(".", "")
    ][0]
    issues = data[software]["vulnerabilities"]
    finding = [
        issue
        for issue in issues
        if _hash_identifiers(issue["identifiers"]) == hashed_id
    ]

    if finding:
        return {
            "description": _create_description(finding[0]),
            "severity": finding[0]["severity"],
            "source": RETIREJS_SOURCE,
            "information updated": datetime.datetime.now().strftime(
                "%d-%m-%Y %H:%M:%S"
            ),
        }

    return {"description": "Not found"}


def _hash_identifiers(identifiers: Dict[str, Union[str, List[str]]]) -> str:
    pre_hash = ""
    for identifier in identifiers.values():
        pre_hash += "".join(identifier)
    return hashlib.sha1(pre_hash.encode()).hexdigest()[:4]


def _create_description(finding: dict) -> str:
    if "summary" in finding["identifiers"]:
        description = finding["identifiers"]["summary"] + ". More information at: "
    else:
        description = "No summary available. Find more information at: "

    info = finding["info"]
    description += ", ".join(info[:-1])
    if len(info) > 1:
        description += " or " + info[-1]
    else:
        description += info[0]

    return description


def cwe_info(cwe_id: str) -> dict:
    """Uses the cwe module to find cwe descriptions"""
    db = Database()
    weakness = db.get(cwe_id.split("-")[1])
    if weakness:
        return {
            "description": weakness.description,
            "source": "https://cwe.mitre.org/index.html",
            "information updated": datetime.datetime.now().strftime(
                "%d-%m-%Y %H:%M:%S"
            ),
        }
    return {"description": "Not found"}


def iana_service_table(search_query: str) -> List[_Service]:
    services = []

    response = requests.get(
        "https://www.iana.org/assignments/service-names-port-numbers/"
        "service-names-port-numbers.xhtml?search=" + search_query
    )
    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.select_one("table#table-service-names-port-numbers")

    if not table:
        return []

    for item in table.select("tbody tr"):
        columns = [col.text for col in item.find_all("td")[:4]]
        name, port, transport_protocol, description = columns

        try:
            if name == search_query:
                service = _Service(
                    name,
                    int(port) if port else None,
                    transport_protocol if transport_protocol else None,
                    description,
                )
                services.append(service)
        except:
            # just ignore on parse errors
            pass
    return services


def service_info(value) -> Tuple[str, str]:
    """Provides information about IP Services such as common assigned ports for certain protocols and descriptions"""
    services = iana_service_table(value)
    source = (
        "https://www.iana.org/assignments/service-names-port-numbers/"
        "service-names-port-numbers.xhtml"
    )
    if not services:
        return f"No description found for {value}", "No source found"

    descriptions = []
    for service in services:
        descriptions.append(
            f"Service is usually on port {service.port}, with protocol {service.transport_protocol}: {service.description}"
        )

    return ". ".join(descriptions), source


# from: https://newbedev.com/how-to-parse-table-with-rowspan-and-colspan
def table_to_2d(table_tag):
    rowspans = []  # track pending rowspans
    rows = table_tag.find_all("tr")

    # first scan, see how many column_names we need
    colcount = 0
    for r, row in enumerate(rows):
        cells = row.find_all(["td", "th"], recursive=False)
        # count column_names (including spanned).
        # add active rowspans from preceding rows
        # we *ignore* the colspan value on the last cell, to prevent
        # creating 'phantom' column_names with no actual cells, only extended
        # colspans. This is achieved by hardcoding the last cell width as 1.
        # a colspan of 0 means “fill until the end” but can really only apply
        # to the last cell; ignore it elsewhere.
        colcount = max(
            colcount,
            sum(int(c.get("colspan", 1)) or 1 for c in cells[:-1])
            + len(cells[-1:])
            + len(rowspans),
        )
        # update rowspan bookkeeping; 0 is a span to the bottom.
        rowspans += [int(c.get("rowspan", 1)) or len(rows) - r for c in cells]
        rowspans = [s - 1 for s in rowspans if s > 1]

    # it doesn't matter if there are still rowspan numbers 'active'; no extra
    # rows to show in the table means the larger than 1 rowspan numbers in the
    # last table row are ignored.

    # build an empty matrix for all possible cells
    table = [[None] * colcount for row in rows]

    # fill matrix from row data
    rowspans = {}  # track pending rowspans, column number mapping to count
    for row, row_elem in enumerate(rows):
        span_offset = 0  # how many column_names are skipped due to row and colspans
        for col, cell in enumerate(row_elem.find_all(["td", "th"], recursive=False)):
            # adjust for preceding row and colspans
            col += span_offset
            while rowspans.get(col, 0):
                span_offset += 1
                col += 1

            # fill table data
            rowspan = rowspans[col] = int(cell.get("rowspan", 1)) or len(rows) - row
            colspan = int(cell.get("colspan", 1)) or colcount - col
            # next column is offset by the colspan
            span_offset += colspan - 1
            value = cell.get_text()
            for drow, dcol in product(range(rowspan), range(colspan)):
                try:
                    table[row + drow][col + dcol] = value
                    rowspans[col + dcol] = rowspan
                except IndexError:
                    # rowspan or colspan outside the confines of the table
                    pass

        # update rowspan bookkeeping
        rowspans = {c: s - 1 for c, s in rowspans.items() if s > 1}

    return table


def _map_usage_value(value: str):
    value = value.lower().strip()
    return value is not None and value != "" and value != "no"


def wiki_port_tables() -> List[_PortInfo]:
    response = requests.get(
        "https://en.wikipedia.org/wiki/List_of_TCP_and_UDP_port_numbers"
    )
    soup = BeautifulSoup(response.text, "html.parser")

    rows = []
    for table in soup.select("table.wikitable.sortable"):
        rows.extend(table_to_2d(table))

    del rows[:2]

    items = []
    for row in rows:
        try:
            port, tcp, udp, _, _, description = row
            port = int(port)
            protocols = []
            if _map_usage_value(tcp):
                protocols.append("tcp")
            if _map_usage_value(tcp):
                protocols.append("udp")
            description = description.strip()
        except:
            continue

        items.append(_PortInfo(port, protocols, description))

    return items


def port_info(number: str, protocol: str) -> Tuple[str, str]:
    """Provides possible or common protocols for operation of network applications behind TCP and UDP ports"""
    items = wiki_port_tables()
    source = "https://en.wikipedia.org/wiki/List_of_TCP_and_UDP_port_numbers"
    descriptions = []
    if not items:
        return (
            f"No description found in wiki table for port {number} with protocol {protocol}",
            source,
        )

    for item in items:
        if item.port == int(number) and protocol.lower() in item.protocols:
            descriptions.append(item.description)

    return ". ".join(descriptions), source


def get_info(ooi_type: str, natural_key: str) -> dict:
    """Adds OOI information to the OOI Information table"""
    if ooi_type == "IPPort":
        protocol, port = natural_key.split(SEPARATOR)
        description, source = port_info(port, protocol)
        return {
            "description": description,
            "source": source,
            "information updated": datetime.datetime.now().strftime(
                "%d-%m-%Y %H:%M:%S"
            ),
        }
    if ooi_type == "Service":
        description, source = service_info(natural_key)
        return {
            "description": description,
            "source": source,
            "information updated": datetime.datetime.now().strftime(
                "%d-%m-%Y %H:%M:%S"
            ),
        }
    if ooi_type == "CVEFindingType":
        return cve_info(natural_key)
    if ooi_type == "CWEFindingType":
        return cwe_info(natural_key)
    if ooi_type == "RetireJSFindingType":
        return retirejs_info(natural_key)
    if ooi_type == "SnykFindingType":
        return snyk_info(natural_key)
    return {"description": ""}
