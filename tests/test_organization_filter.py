from django.urls import reverse

from objects.models import Finding, FindingType, Hostname, Network
from plugins.models import Plugin
from tasks.models import Schedule, Task


def test_task_list_filtered_by_organization(client, client_user_two_organizations, organization, organization_b, xtdb):
    """Test that task list can be filtered by single organization."""
    client.force_login(client_user_two_organizations)
    Task.objects.create(organization=organization, type="plugin", data={"plugin_id": "test_plugin"})
    Task.objects.create(organization=organization_b, type="plugin", data={"plugin_id": "test_plugin"})

    # Get all tasks
    response = client.get(reverse("task_list"))
    assert response.status_code == 200
    assert len(response.context["object_list"]) == 2
    assert "filtered_organizations" not in response.context

    # Filter by single organization
    response = client.get(reverse("task_list") + "?organization=org")
    assert response.status_code == 200
    assert len(response.context["object_list"]) == 1
    assert response.context["object_list"][0].organization == organization
    assert response.context["filtered_organizations"] == [organization]
    assert response.context["organization"] == organization

    # Filter by organization_b
    response = client.get(reverse("task_list") + "?organization=org_b")
    assert response.status_code == 200
    assert len(response.context["object_list"]) == 1
    assert response.context["object_list"][0].organization == organization_b

    # Filter by non-existent organization
    response = client.get(reverse("task_list") + "?organization=nonexistent")
    assert response.status_code == 200
    assert len(response.context["object_list"]) == 0


def test_task_list_filtered_by_multiple_organizations(
    client, client_user_two_organizations, organization, organization_b, xtdb
):
    """Test that task list can be filtered by multiple organizations."""
    client.force_login(client_user_two_organizations)
    Task.objects.create(organization=organization, type="plugin", data={"plugin_id": "test_plugin"})
    Task.objects.create(organization=organization_b, type="plugin", data={"plugin_id": "test_plugin"})

    # Filter by both organizations
    response = client.get(reverse("task_list") + "?organization=org&organization=org_b")
    assert response.status_code == 200
    assert len(response.context["object_list"]) == 2
    assert len(response.context["filtered_organizations"]) == 2
    assert organization in response.context["filtered_organizations"]
    assert organization_b in response.context["filtered_organizations"]


def test_task_detail_filtered_by_organization(
    client, client_user_two_organizations, organization, organization_b, xtdb
):
    client.force_login(client_user_two_organizations)
    Plugin.objects.create(plugin_id="test_plugin", name="test")
    task1 = Task.objects.create(organization=organization, type="plugin", data={"plugin_id": "test_plugin"})

    response = client.get(reverse("task_detail", kwargs={"pk": task1.id}))
    assert response.status_code == 200

    response = client.get(reverse("task_detail", kwargs={"pk": task1.id}) + "?organization=org")
    assert response.status_code == 200

    response = client.get(reverse("task_detail", kwargs={"pk": task1.id}) + "?organization=org_b")
    assert response.status_code == 404


def test_schedule_list_filtered_by_organization(
    client, client_user_two_organizations, organization, organization_b, xtdb
):
    client.force_login(client_user_two_organizations)

    Schedule.objects.create(organization=organization, enabled=True)
    Schedule.objects.create(organization=organization_b, enabled=True)

    response = client.get(reverse("schedule_list"))
    assert response.status_code == 200
    assert len(response.context["object_list"]) == 2

    response = client.get(reverse("schedule_list") + "?organization=org")
    assert response.status_code == 200
    assert len(response.context["object_list"]) == 1
    assert response.context["object_list"][0].organization == organization

    response = client.get(reverse("schedule_list") + "?organization=org_b")
    assert response.status_code == 200
    assert len(response.context["object_list"]) == 1
    assert response.context["object_list"][0].organization == organization_b


def test_schedule_detail_filtered_by_organization(client, client_user_two_organizations, organization, xtdb):
    client.force_login(client_user_two_organizations)
    schedule1 = Schedule.objects.create(organization=organization, enabled=True)

    response = client.get(reverse("schedule_detail", kwargs={"pk": schedule1.id}))
    assert response.status_code == 200

    response = client.get(reverse("schedule_detail", kwargs={"pk": schedule1.id}) + "?organization=org")
    assert response.status_code == 200


def test_finding_list_filtered_by_organization(
    client, client_user_two_organizations, organization, organization_b, xtdb
):
    client.force_login(client_user_two_organizations)

    network = Network.objects.create(name="test-network")
    hostname1 = Hostname.objects.create(name="test1.example.com", network=network)
    hostname2 = Hostname.objects.create(name="test2.example.com", network=network)

    finding_type = FindingType.objects.create(code="TEST-001", description="Test finding type")

    Finding.objects.create(
        organization=organization, finding_type=finding_type, object_type="hostname", object_id=hostname1.id
    )
    Finding.objects.create(
        organization=organization_b, finding_type=finding_type, object_type="hostname", object_id=hostname2.id
    )

    response = client.get(reverse("objects:finding_list"))
    assert response.status_code == 200
    assert len(response.context["object_list"]) == 2

    response = client.get(reverse("objects:finding_list") + "?organization=org")
    assert response.status_code == 200
    assert len(response.context["object_list"]) == 1
    assert response.context["object_list"][0].organization == organization

    response = client.get(reverse("objects:finding_list") + "?organization=org_b")
    assert response.status_code == 200
    assert len(response.context["object_list"]) == 1
    assert response.context["object_list"][0].organization == organization_b
