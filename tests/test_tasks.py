import datetime

from katalogus.models import BoefjeConfig
from katalogus.worker.job_models import BoefjeMeta
from katalogus.worker.models import Boefje
from octopoes.models.pagination import Paginated
from tasks.models import Task
from tasks.tasks import get_expired_boefjes


def test_expired_boefjes(organization, dns_records, katalogus_client, octopoes_api_connector, hostname):
    octopoes_api_connector.list_objects.return_value = Paginated(count=1, items=[hostname])
    assert get_expired_boefjes() == []
    katalogus_client.enable_plugin(organization.code, dns_records)
    config = BoefjeConfig.objects.first()

    assert get_expired_boefjes() == [(hostname, config)]
    assert get_expired_boefjes(organization=organization.code) == [(hostname, config)]
    assert get_expired_boefjes(organization=organization.code, input_oois=[]) == []
    assert get_expired_boefjes(organization="no") == []

    katalogus_client.enable_plugin(organization.code, dns_records)
    boefje_meta = BoefjeMeta(
        boefje=Boefje(
            id=dns_records.id,
            plugin_id=dns_records.plugin_id,
            name=dns_records.name,
            version=dns_records.version,
            oci_image=dns_records.oci_image,
            oci_arguments=dns_records.oci_arguments,
        ),
        input_ooi=hostname.primary_key,
        input_ooi_data=hostname.serialize(),
        organization=organization.code,
    )
    task = Task.objects.create(type="boefje", organization=organization, data=boefje_meta.model_dump(mode="json"))

    assert get_expired_boefjes() == []

    task.created_at = datetime.datetime.now() - datetime.timedelta(minutes=1400)
    task.save()
    assert get_expired_boefjes() == []

    task.created_at = datetime.datetime.now() - datetime.timedelta(minutes=1450)
    task.save()
    assert get_expired_boefjes() == [(hostname, config)]

    katalogus_client.disable_plugin(organization.code, dns_records)

    assert get_expired_boefjes() == []
