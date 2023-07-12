import json
from typing import Dict, Iterable, Union

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI
from octopoes.models.ooi.findings import Finding, KATFindingType


def parse_cipher(cipher: str) -> Dict:
    parts = cipher.split()

    cipher_dict = {
        "protocol": parts[0],
        "cipher_suite_code": parts[1],
        "cipher_suite_name": parts[2],
        "key_exchange_algorithm": parts[3],
        "size": parts[4],
        "encryption_algorithm": parts[5],
        "key_size": parts[6],
        "cipher_suite_alias": parts[7],
    }

    return cipher_dict


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterable[OOI]:
    boefje_meta = normalizer_meta.raw_data.boefje_meta
    input_ooi = boefje_meta.input_ooi

    output = json.loads(raw)

    tls1_2 = []
    tls1_3 = []

    for item in output:
        if "cipher-tls1_2" in item["id"]:
            tls1_2.append(parse_cipher(item["finding"]))
        if "cipher-tls1_3" in item["id"]:
            tls1_3.append(parse_cipher(item["finding"]))

    all_ciphers = tls1_2 + tls1_3

    sufficient_ciphers = []
    bad_ciphers = []
    unknown_ciphers = []

    # open ciphers.json
    with open("boefjes/plugins/kat_ssl_test_ciphers/ciphers.json") as f:
        cipher_scores = json.load(f)
        for cipher in all_ciphers:
            code = cipher["cipher_suite_alias"]
            if code in cipher_scores["sufficient"]:
                sufficient_ciphers.append(code)
            elif code in cipher_scores["bad"]:
                bad_ciphers.append(code)
            elif code not in cipher_scores["good"]:
                unknown_ciphers.append(code)

    if sufficient_ciphers:
        ft = KATFindingType(id="KAT-SUFFICIENT-CIPHERS")
        yield ft
        yield Finding(
            ooi=input_ooi,
            finding_type=ft.reference,
            description=f"Sufficient ciphers found: {' '.join(sufficient_ciphers)}",
        )

    if bad_ciphers:
        ft = KATFindingType(id="KAT-BAD-CIPHERS")
        yield ft
        yield Finding(
            ooi=input_ooi,
            finding_type=ft.reference,
            description=f"Bad ciphers found: {' '.join(sufficient_ciphers)}",
        )

    if unknown_ciphers:
        ft = KATFindingType(id="KAT-UNKNOWN-CIPHERS")
        yield ft
        yield Finding(
            ooi=input_ooi,
            finding_type=ft.reference,
            description=f"Unknown ciphers found: {' '.join(sufficient_ciphers)}",
        )
