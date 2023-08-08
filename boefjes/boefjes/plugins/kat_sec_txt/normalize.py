import json
from typing import Iterable, Union

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import Finding, KATFindingType


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterable[OOI]:
    results = json.loads(raw)
    boefje_meta = normalizer_meta.raw_data.boefje_meta
    ooi_ref = Reference.from_str(boefje_meta.input_ooi)

    invalid = {
        "location",
        "invalid_cert",
        "invalid_uri_scheme",
        "invalid_media",
        "no_expire",
        "expired",
        "no_contact",
        "no_canonical_match",
        "invalid_lang",
    }

    bad_format = {
        "no_content_type",
        "invalid_media",
        "invalid_charset",
        "utf8",
        "multi_lang",
        "no_uri",
        "no_https",
        "invalid_expiry",
        "prec_ws",
        "no_space",
        "empty_key",
        "invalid_line",
        "no_line_seperators",
        "signed_format_issue",
        "data_after_sig",
        "no_csaf_file",
    }

    errors_total = ""
    errors_list = []
    for error in results["errors"]:
        if error["code"] not in errors_list:
            errors_list.append(str(error["code"]))
            errors_total = errors_total + "\n" + str(len(errors_list)) + " " + str(error["message"])
    errors_list = set(errors_list)

    if results["valid"] is False:
        if results["errors"][0]["code"] == "no_security_txt" or (
            "invalid_media" in errors_list and len(results["errors"]) > 5
        ):
            kft = KATFindingType(id="KAT-NO-SECURITY-TXT")
            errors_total = "Security.txt is missing for this hostname"
        else:
            if errors_list & invalid:
                kft = KATFindingType(id="KAT-INVALID-SECURITY-TXT")
            elif errors_list & bad_format:
                kft = KATFindingType(id="KAT-BAD-FORMAT-SECURITY-TXT")
        yield kft

        finding = Finding(finding_type=kft.reference, ooi=ooi_ref, description=errors_total)
        yield finding
