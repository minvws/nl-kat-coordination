import json
import math
from typing import Tuple, Union, Dict, List

from pybinaryedge import BinaryEdge

from config import settings
from job import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> Tuple[BoefjeMeta, Union[bytes, str]]:

    be = BinaryEdge(settings.binaryedge_api)
    results: Dict[str, List] = {"results": []}

    input_ = boefje_meta.arguments["input"]

    if input_["ooi_type"] in ["IPAddressV4", "IPAddressV6"]:
        ip = input_["address"]
        result = be.host(ip)

        # create same result-structure as netblock
        for event in result["events"]:
            results["results"].extend(event["results"])
    elif input_["ooi_type"] in ["IPV4NetBlock", "IPV6NetBlock"]:
        netblock = input_["mask"]
        dork = f'ip:"{netblock}"'

        # iterate through partial results
        page_counter = 0
        total_pages = 1  # set real value after first request

        while page_counter < total_pages:
            page_counter += 1
            result = be.host_search(dork, page_counter)

            # calculate number of existing pages
            if page_counter == 1:
                total_pages = math.ceil(result["total"] / result["pagesize"])

            results["results"].extend(result["events"])

    return boefje_meta, json.dumps(results)
