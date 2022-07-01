import json
from typing import Iterator, Union

from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import Finding, CVEFindingType
from wpscan_out_parse import WPScanJsonParser

from job import NormalizerMeta


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
    url_reference = Reference.from_str(normalizer_meta.boefje_meta.input_ooi)

    if raw:
        data = json.loads(raw.decode())
        results = WPScanJsonParser(data)
        for alert in results.get_alerts():
            lines = alert.splitlines()
            for line in lines:
                if "CVE: " in line:
                    cve = line.split("=")
                    id_ = cve[-1]
                    if "CVE-" in id_:
                        ft = CVEFindingType(id=id_)
                        yield ft
                        finding = Finding(
                            finding_type=ft.reference,
                            ooi=url_reference,
                            description=alert.splitlines()[0],
                        )
                        yield finding
