import json
from collections.abc import Iterable

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI, Reference
from octopoes.models.ooi.network import Network
from octopoes.models.ooi.software import Software, SoftwareInstance
from octopoes.models.ooi.web import URL


def run(normalizer_meta: NormalizerMeta, raw: bytes | str) -> Iterable[OOI]:
    results = json.loads(raw)
    boefje_meta = normalizer_meta.raw_data.boefje_meta

    input_ = boefje_meta.arguments["input"]
    hostname = input_["netloc"]["name"]
    path = input_["path"]
    scheme = input_["scheme"]
    url = f"{scheme}://{hostname}{path}"

    pk = boefje_meta.input_ooi
    hostname_reference = Reference.from_str(pk)

    original_url_status = results["urls"][url]["status"]

    if 300 <= original_url_status < 400:
        # The requested url was redirected, so only return the new url instance. If needed we rescan the new url.
        results["urls"].pop(url)

        for redirected_url in results["urls"]:
            yield URL(
                network=Network(name=hostname_reference.tokenized.netloc.network.name).reference, raw=redirected_url
            )

        return

    for technology in results["technologies"]:
        s = Software(
            name=technology["name"],
            version=technology["version"],
            cpe=technology["cpe"],
        )
        si = SoftwareInstance(ooi=hostname_reference, software=s.reference)
        yield s
        yield si
