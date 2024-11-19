import json
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

from tanimachi import (
    Categories,
    Fingerprints,
    Groups,
    Har,
    Wappalyzer,
)
from tanimachi.schemas import Log, Entry
from tanimachi.schemas.har import (
    Creator,
    Cache,
    Timings,
    Request,
    Header,
    Response,
    Cookie,
    Content,
)

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
    raw_respsone, raw_body = raw.split(b"\n\n", 1)
    response_object = json.loads(raw_respsone)
    url = response_object["response"]["url"]

    headers = response_object["response"]["headers"]
    body = raw_body.decode(response_object.get("encoding") or "utf-8", "replace")

    # with Path(__file__).parent.joinpath("technologies.json").open() as f:
    #     data = json.load(f)
    # wappalyzer = Wappalyzer(categories=data["categories"], technologies=data["technologies"])
    # web_page = WebPage(url, body, headers)
    #
    # results = asyncio.run(wappalyzer.analyze_with_versions_and_categories(web_page))

    fingerprints = Fingerprints.model_validate_pattern(
        "/Users/ammar/Downloads/webappanalyzer/src/technologies/*.json"
    )
    categories = Categories.model_validate_file(
        "/Users/ammar/Downloads/webappanalyzer/src/categories.json"
    )
    groups = Groups.model_validate_file(
        "/Users/ammar/Downloads/webappanalyzer/src/groups.json"
    )
    # har = Har.model_validate_file(
    #     "/Users/ammar/Downloads/tanimachi/tests/fixtures/har/example.har"
    # )
    #

    # create a Har model based on the response object
    har = Har(
        log=Log(
            version="1.2",
            creator=Creator(name="OpenKAT", version="0"),
            entries=[
                Entry(
                    pageref=None,
                    startedDateTime=datetime.now(tz=timezone.utc),
                    time=0,
                    request=Request(
                        method=response_object["request"]["method"],
                        url=url,
                        httpVersion="",
                        cookies=[],
                        headers=[
                            Header(name=key, value=value)
                            for key, value in response_object["request"][
                                "headers"
                            ].items()
                        ],
                        queryString=[],
                        headersSize=-1,
                        bodySize=0,
                    ),
                    response=Response(
                        status=response_object["response"]["status_code"],
                        statusText="",
                        httpVersion="",
                        cookies=[
                            Cookie(name=key, value=value)
                            for key, value in response_object["response"][
                                "cookies"
                            ].items()
                        ],
                        headers=[
                            Header(name=key, value=value)
                            for key, value in response_object["response"][
                                "headers"
                            ].items()
                        ],
                        content=Content(
                            size=len(body),
                            mimeType=response_object["response"]["headers"].get(
                                "Content-Type", "text/html"
                            ),
                            text=body,
                        ),
                        redirectURL="",
                        headersSize=-1,
                        bodySize=0,
                    ),
                    cache=Cache(),
                    timings=Timings(send=0, wait=0, receive=0),
                )
            ],
        )
    )

    wappalyzer = Wappalyzer(fingerprints, categories=categories, groups=groups)
    detections = wappalyzer.analyze(har)

    for detection in detections:
        cpe = detection.fingerprint.cpe
        version = cpe.split(":")[1] if cpe else None
        software = Software(name=detection.fingerprint.id, version=version, cpe=cpe)
        software_instance = SoftwareInstance(
            ooi=web_url.reference, software=software.reference
        )
        yield from [software, software_instance]
