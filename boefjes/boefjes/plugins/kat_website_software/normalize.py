import json
from typing import Generator, Union

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI, Reference
from octopoes.models.ooi.software import Software, SoftwareInstance


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Generator[OOI]:
    results = json.loads(raw)
    boefje_meta = normalizer_meta.raw_data.boefje_meta
    pk = boefje_meta.input_ooi

    hostname_reference = Reference.from_str(pk)

    for technology in results["technologies"]:
        s = Software(
            name=technology["name"],
            version=technology["version"],
            cpe=technology["cpe"],
        )
        si = SoftwareInstance(ooi=hostname_reference, software=s.reference)
        yield s
        yield si
