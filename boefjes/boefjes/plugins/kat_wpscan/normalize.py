import json
from collections.abc import Iterable

from wpscan_out_parse import WPScanJsonParser

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import CVEFindingType, Finding


def run(normalizer_meta: NormalizerMeta, raw: bytes | str) -> Iterable[OOI]:
    url_reference = Reference.from_str(normalizer_meta.raw_data.boefje_meta.input_ooi)

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
