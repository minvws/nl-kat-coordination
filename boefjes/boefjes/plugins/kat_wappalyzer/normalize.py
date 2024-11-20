from collections.abc import Iterable
from pathlib import Path

from tanimachi import Categories, Fingerprints, Groups, Har, Wappalyzer

from boefjes.job_models import NormalizerOutput
from octopoes.models import Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import Network
from octopoes.models.ooi.software import Software, SoftwareInstance
from octopoes.models.ooi.web import HostnameHTTPURL


def run(input_ooi: dict, raw: bytes) -> Iterable[NormalizerOutput]:
    pk = input_ooi["primary_key"]
    tokenized_weburl = Reference.from_str(pk).tokenized["web_url"]
    tokenized_hostname = Reference.from_str(pk).tokenized["website"]["hostname"]

    network = Network(name=tokenized_hostname["network"]["name"])
    hostname = Hostname(network=network.reference, name=tokenized_hostname["name"])
    web_url = HostnameHTTPURL(
        network=network.reference,
        netloc=hostname.reference,
        port=tokenized_weburl["port"],
        scheme=tokenized_weburl["scheme"],
        path=tokenized_weburl["path"],
    )

    data_directory = Path(__file__).parent / "data"
    fingerprints = Fingerprints.model_validate_pattern(data_directory.joinpath("technologies/*.json").as_posix())
    categories = Categories.model_validate_file(data_directory.joinpath("categories.json"))
    groups = Groups.model_validate_file(data_directory.joinpath("groups.json"))

    har = Har.model_validate_json(raw)

    wappalyzer = Wappalyzer(fingerprints, categories=categories, groups=groups)
    detections = wappalyzer.analyze(har)

    for detection in detections:
        cpe = detection.fingerprint.cpe
        version = cpe.split(":")[1] if cpe else None
        software = Software(name=detection.fingerprint.id, version=version, cpe=cpe)
        software_instance = SoftwareInstance(ooi=web_url.reference, software=software.reference)
        yield from [software, software_instance]
