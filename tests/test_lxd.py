from unittest import TestCase, skip

from boefjes.job import BoefjeMeta, Boefje
from boefjes.katalogus.models import Boefje as PluginBoefje
from boefjes.lxd.lxd_runner import LXDBoefjeJobRunner

EXAMPLE_JOB = BoefjeMeta(
    id="test-job",
    boefje=Boefje(**{"id": "dns-records", "name": "DnsRecords", "version": "9"}),
    input_ooi="Hostname|internet|example.com",
    arguments={"input": {"TODO": "TODO"}},
    organization="test",
)


class KATalogusTest(TestCase):
    def setUp(self) -> None:
        self.job_runner = LXDBoefjeJobRunner(
            EXAMPLE_JOB,
            PluginBoefje(
                id=EXAMPLE_JOB.boefje.id,
                repository_id="test-repo",
                consumes={"Network"},
                produces=["text/plain"],
            ),
        )

    @skip("Needs LXD daemon setup.")
    def test_lxd(self):
        updated_job_meta, job_output = self.job_runner.run()
