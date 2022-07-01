from octopoes.models.types import (
    IPAddressV4,
    IPAddressV6,
    IPPort,
    Service,
    IPService,
)

from boefjes.models import Boefje, Normalizer, SCAN_LEVEL

# NMAPTcpFull = Boefje(
#     id="nmap-tcp-full",
#     name="Nmap TCP (Full)",
#     module="kat_nmap.main",
#     description="Scan all TCP ports. Including service detection",
#     consumes={IPAddressV4, IPAddressV6},
#     dispatches={"normalizers": ["kat_nmap_normalize"], "boefjes": []},
#     produces={IPAddressV4, IPAddressV6, IPPort, Service, IPService},
# )

NMAPTcpTop250 = Boefje(
    id="nmap-tcp-top250",
    name="Nmap TCP (Top 250)",
    module="kat_nmap.main",
    description="Scan top 250 TCP ports. Including service detection",
    consumes={"IPAddressV4", "IPAddressV6"},
    produces={"IPAddressV4", "IPAddressV6", "IPPort", "Service", "IPService"},
    scan_level=SCAN_LEVEL.L2,
)

# NMAPUdpFull = Boefje(
#     id="nmap-udp-full",
#     name="Nmap UDP (Full)",
#     module="kat_nmap.main",
#     description="Scan all UDP ports. Including service detection",
#     consumes={IPAddressV4, IPAddressV6},
#     dispatches={"normalizers": ["kat_nmap_normalize"], "boefjes": []},
#     produces={IPAddressV4, IPAddressV6, IPPort, Service, IPService},
# )
#
# NMAPUdpTop250 = Boefje(
#     id="nmap-udp-top250",
#     name="Nmap UDP (Top 250)",
#     module="kat_nmap.main",
#     description="Scan top 250 UDP ports. Including service detection",
#     consumes={IPAddressV4, IPAddressV6},
#     dispatches={"normalizers": ["kat_nmap_normalize"], "boefjes": []},
#     produces={IPAddressV4, IPAddressV6, IPPort, Service, IPService},
# )

# BOEFJES = [NMAPUdpTop250, NMAPUdpFull, NMAPTcpFull, NMAPTcpTop250]
BOEFJES = [NMAPTcpTop250]
NORMALIZERS = [
    Normalizer(
        name="kat_nmap_normalize",
        module="kat_nmap.normalize",
        consumes=[NMAPTcpTop250.id],
        produces=NMAPTcpTop250.produces,
    )
]
