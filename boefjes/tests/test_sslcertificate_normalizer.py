from boefjes.job_models import NormalizerMeta
from boefjes.plugins.kat_ssl_certificates.normalize import run
from tests.loading import get_dummy_data


def test_ssl_certificates_normalizer():
    meta = NormalizerMeta.model_validate_json(get_dummy_data("ssl-certificates-normalize.json"))

    output = list(run(meta, get_dummy_data("ssl-certificates.txt")))

    assert len([ooi for ooi in output if ooi.object_type == "X509Certificate"]) == 3
