import ipaddress
import json
from typing import Iterator, Union

from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import KATFindingType, Finding
from octopoes.models.ooi.network import (
    IPPort,
    Protocol,
    PortState,
    IPAddressV4,
    IPAddressV6,
    Network,
)

from job import NormalizerMeta


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
    results = json.loads(raw)
    boefje_meta = normalizer_meta.boefje_meta
    input_ = boefje_meta.arguments["input"]
    pk_ooi = Reference.from_str(boefje_meta.input_ooi)
    network = Network(name="internet").reference

    # Structure based on https://docs.binaryedge.io/modules/<accepted_modules_name>/
    accepted_modules = ("ssl-simple", "sslv2", "jarm")
    for scan in results["results"]:
        module = scan["origin"]["type"]
        if module not in accepted_modules:
            continue

        port_nr = int(scan["target"]["port"])
        protocol = scan["target"]["protocol"]
        ip = scan["target"]["ip"]

        if input_["ooi_type"] in ["IPAddressV4", "IPAddressV6"]:
            ip_ref = pk_ooi
        else:
            ipvx = ipaddress.ip_address(ip)
            if ipvx.version == 4:
                ip_ooi = IPAddressV4(
                    address=ip,
                    network=network,
                )
            else:
                ip_ooi = IPAddressV6(
                    address=ip,
                    network=network,
                )
            yield ip_ooi
            ip_ref = ip_ooi.reference

        ip_port_ooi = IPPort(
            address=ip_ref,
            protocol=Protocol(protocol),
            port=port_nr,
            state=PortState("open"),
        )
        yield ip_port_ooi

        # (potential) TODO: result.data.server_info {openssl_cipher_string_supported,highest_ssl_version_supported,ja3,ja3_digest}
        # (potential) TODO: version
        # (potential) TODO: jarm
        for cert_chain in (
            scan.get("data", {}).get("cert_info", {}).get("certificate_chain", [])
        ):
            pass
            # yield Certificate(
            #     subject = cert_chain['as_dict']['subject']['common_name'],
            #     issuer = cert_chain['as_dict']['issuer']['common_name'],
            #     valid_from = cert_chain['as_dict']['validity']['not_before'],
            #     valid_until = cert_chain['as_dict']['validity']['not_after'],
            #     pk_algorithm = cert_chain['as_dict']['public_key_info']['algorithm'],
            #     pk_size = cert_chain['as_dict']['public_key_info']['key_size'],
            #     pk_number = ,  # FIXME: determine how to get this value
            #     # Optional: hostname_ooi, certificate_ooi
            # )

        vulns = scan.get("data", {}).get("vulnerabilities", {})
        if vulns.get("compression", {}).get("supports_compression"):
            kat_ooi = KATFindingType(id="KAT-642")
            yield kat_ooi
            yield Finding(
                finding_type=kat_ooi.reference,
                ooi=ip_port_ooi.reference,
                description=f"SSL is set to support compression, but it is advised to disable this.",
            )
        if vulns.get("fallback", {}).get("supports_fallback_scsv"):
            kat_ooi = KATFindingType(id="KAT-642")
            yield kat_ooi
            yield Finding(
                finding_type=kat_ooi.reference,
                ooi=ip_port_ooi.reference,
                description=f"SSL is set to support fallback scsv, but it is advised to disable this.",
            )
        if "heartbleed" in vulns and vulns["heartbleed"]["is_vulnerable_to_heartbleed"]:
            kat_ooi = KATFindingType(id="KAT-642")
            yield kat_ooi
            yield Finding(
                finding_type=kat_ooi.reference,
                ooi=ip_port_ooi.reference,
                description=f"It is confirmed this connection is vulnerable to Heartbleed, it is advised to adopt the fix.",
            )
        if (
            "openssl_ccs" in vulns
            and vulns["openssl_ccs"]["is_vulnerable_to_ccs_injection"]
        ):
            kat_ooi = KATFindingType(id="KAT-642")
            yield kat_ooi
            yield Finding(
                finding_type=kat_ooi.reference,
                ooi=ip_port_ooi.reference,
                description=f"It is verified this connection is vulnerable to the OpenSSL CSS Injection Vulnerability.",
            )
        if (
            "renegotiation" in vulns
            and vulns["renegotiation"]["accepts_client_renegotiation"]
        ):
            kat_ooi = KATFindingType(id="KAT-642")
            yield kat_ooi
            yield Finding(
                finding_type=kat_ooi.reference,
                ooi=ip_port_ooi.reference,
                description=f"This SSL accepts client renegotiation, but i can be used in a DOS attack.",
            )
        if (
            "renegotiation" in vulns
            and vulns["renegotiation"]["supports_secure_renegotiation"]
        ):
            kat_ooi = KATFindingType(id="KAT-642")
            yield kat_ooi
            yield Finding(
                finding_type=kat_ooi.reference,
                ooi=ip_port_ooi.reference,
                description=f"This SSL accepts secure renegotiation, but i can be used in a DOS attack.",
            )
        if "robot_result_enum" in vulns.get("robot", {}):
            robot = vulns["robot"]["robot_result_enum"]
            if robot == "VULNERABLE_WEAK_ORACLE":
                # FIXME: new KAT-Finding (low)?
                pass  # The server is vulnerable but the attack would take too long
            elif robot == "VULNERABLE_STRONG_ORACLE":
                # FIXME: new KAT-Finding (high)?
                pass  # The server is vulnerable and real attacks are feasible
            elif robot == "NOT_VULNERABLE_NO_ORACLE":
                pass  # The server supports RSA cipher suites but does not act as an oracle
            elif robot == "NOT_VULNERABLE_RSA_NOT_SUPPORTED":
                pass  # The server does not supports RSA cipher suites
            elif robot == "UNKNOWN_INCONSISTENT_RESULTS":
                # FIXME: KATFinding (low)?
                pass  # Could not determine whether the server is vulnerable or not
