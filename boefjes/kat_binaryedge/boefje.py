from boefjes.models import Boefje, Normalizer, SCAN_LEVEL

BinaryEdge = Boefje(
    id="binaryedge",
    name="BinaryEdge",
    description="NEEDS API KEY IN ENV - Use BinaryEdge to find open ports with vulnerabilities that are found on that port",
    consumes={"IPAddressV4", "IPAddressV6"},
    scan_level=SCAN_LEVEL.L2,
    produces={
        "IPService",
        "IPPort",
        "Service",
        "Software",
        "SoftwareInstance",
        "KATFindingType",
        "CVEFindingType",
        "Finding",
    },
)

BOEFJES = [BinaryEdge]
NORMALIZERS = [
    Normalizer(
        name="kat_binaryedge_containers",
        module="kat_binaryedge.normalizers.containers",
        consumes=[BinaryEdge.id],
        produces=BinaryEdge.produces,
    ),
    Normalizer(
        name="kat_binaryedge_databases",
        module="kat_binaryedge.normalizers.databases",
        consumes=[BinaryEdge.id],
        produces=BinaryEdge.produces,
    ),
    Normalizer(
        name="kat_binaryedge_http_web",
        module="kat_binaryedge.normalizers.http_web",
        consumes=[BinaryEdge.id],
        produces=BinaryEdge.produces,
    ),
    Normalizer(
        name="kat_binaryedge_message_queues",
        module="kat_binaryedge.normalizers.message_queues",
        consumes=[BinaryEdge.id],
        produces=BinaryEdge.produces,
    ),
    Normalizer(
        name="kat_binaryedge_protocols",
        module="kat_binaryedge.normalizers.protocols",
        consumes=[BinaryEdge.id],
        produces=BinaryEdge.produces,
    ),
    Normalizer(
        name="kat_binaryedge_remote_desktop",
        module="kat_binaryedge.normalizers.remote_desktop",
        consumes=[BinaryEdge.id],
        produces=BinaryEdge.produces,
    ),
    Normalizer(
        name="kat_binaryedge_service_identification",
        module="kat_binaryedge.normalizers.service_identification",
        consumes=[BinaryEdge.id],
        produces=BinaryEdge.produces,
    ),
    Normalizer(
        name="kat_binaryedge_services",
        module="kat_binaryedge.normalizers.services",
        consumes=[BinaryEdge.id],
        produces=BinaryEdge.produces,
    ),
]
