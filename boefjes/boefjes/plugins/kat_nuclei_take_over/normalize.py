import json
from collections.abc import Iterable

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import Finding, KATFindingType


def run(normalizer_meta: NormalizerMeta, raw: bytes | str) -> Iterable[OOI]:
    url_reference = Reference.from_str(normalizer_meta.raw_data.boefje_meta.input_ooi)
    if raw:
        for line in raw.splitlines():
            # Extract and parse values
            data = json.loads(line)
            info = data["info"]["name"]
            curl_command = data["curl-command"]

            # Create instances of CVEFindingType and Finding classes
            kft = KATFindingType(id="SUB-DOMAIN-TAKEOVER")
            yield kft

            finding = Finding(
                finding_type=kft.reference,
                ooi=url_reference,
                proof=curl_command,
                description=info,
                reproduce=None,  # Set this attribute if you have a reproduce value
            )
            yield finding
