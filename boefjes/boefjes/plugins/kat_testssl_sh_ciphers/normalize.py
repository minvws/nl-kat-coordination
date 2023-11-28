import json
from typing import Dict, Iterable, Union

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI, Reference
from octopoes.models.ooi.service import TLSCipher


def parse_cipher(cipher: Dict) -> Union[Dict, None]:
    if cipher["id"].startswith("cipher-tls"):
        parts = cipher["finding"].split()

        cipher_dict = {
            parts[0]: {  # parts[0] is the protocol
                "cipher_suite_code": parts[1],
                "cipher_suite_name": parts[2],
                "key_exchange_algorithm": parts[3],
            }
        }

        # if key size is found
        if parts[4].isdigit():
            cipher_dict[parts[0]].update(
                {
                    "key_size": int(parts[4]),
                    "encryption_algorithm": parts[5],
                    "bits": int(parts[6]),
                    "cipher_suite_alias": parts[7],
                }
            )
        else:
            cipher_dict[parts[0]].update(
                {
                    "encryption_algorithm": parts[4],
                    "bits": int(parts[5]),
                    "cipher_suite_alias": parts[6],
                }
            )

        return cipher_dict


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterable[OOI]:
    boefje_meta = normalizer_meta.raw_data.boefje_meta
    input_ooi = Reference.from_str(boefje_meta.input_ooi)
    output = json.loads(raw)

    tls_dict = {}
    for item in output:
        cipher = parse_cipher(item)
        if cipher:
            for protocol, suite in cipher.items():
                if protocol not in tls_dict:
                    tls_dict[protocol] = []
                tls_dict[protocol].append(suite)
    if tls_dict:
        yield TLSCipher(ip_service=input_ooi, suites=tls_dict)
