import json
from typing import Union, Iterator

from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import Finding, CVEFindingType

from boefjes.job_models import NormalizerMeta


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
    url_reference = Reference.from_str(normalizer_meta.raw_data.boefje_meta.input_ooi)
    if raw:
        for line in raw.splitlines():
            # Extract and parse values
            data = json.loads(line)
            id_ = data["info"]["classification"]["cve-id"][0]
            description = data["info"]["description"]
            curl_command = data["curl-command"]

            # Create instances of CVEFindingType and Finding classes
            cve_finding_type = CVEFindingType(id=id_)
            yield cve_finding_type

            finding = Finding(
                finding_type=cve_finding_type.reference,
                ooi=url_reference,
                proof=curl_command,
                description=description,
                reproduce=None,  # Set this attribute if you have a reproduce value
            )
            yield finding
