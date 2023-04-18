import json
import logging
from typing import List, Tuple, Union

from pynetdicom import AE

from boefjes.job_models import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    input_ = boefje_meta.arguments["input"]
    ip = input_["address"]

    # it prints errors if the port is not open, ignore these errors as we expect them to happen a lot
    logging.getLogger("pynetdicom").setLevel(logging.CRITICAL)

    # An AE is an Application Entity, a DICOM specific thing
    ae = AE()

    # Context is a DICOM term used to define the content and encoding of data (like a DICOM dataset)
    # This specific context is used to verify a Service-Object Pair (SOP) class - basically connection establishment
    ae.add_requested_context("1.2.840.10008.1.1")

    # Default ports
    ports = (11112, 104, 2761, 2762)
    results = {"open_ports": []}

    # Attempt to establish connection and post result
    for port in ports:
        assoc = ae.associate(ip, port)

        if assoc.is_established:
            assoc.release()
            results["open_ports"].append(port)
        else:
            assoc.abort()

    ae.remove_requested_context("1.2.840.10008.1.1")

    return [(set(), json.dumps(results))]
