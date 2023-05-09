import json

from katalogus.views.plugin_detail import PluginDetailView
from pytest_django.asserts import assertContains

from tests.conftest import setup_request


def test_plugin_detail_view(
    rf,
    superuser_member,
    mock_mixins_katalogus,
    plugin_details,
    mock_organization_view_octopoes,
    mocker,
):
    mock_mixins_katalogus().get_plugin.return_value = plugin_details
    mock_scheduler_client_session = mocker.patch("rocky.scheduler.client.session")
    scheduler_return_value = mocker.MagicMock()
    scheduler_return_value.text = json.dumps(
        {
            "count": 1,
            "next": "http://scheduler:8000/tasks?scheduler_id=boefje-test&type=boefje&plugin_id=test_plugin&limit=10&offset=10",
            "previous": None,
            "results": [
                {
                    "id": "2e757dd3-66c7-46b8-9987-7cd18252cc6d",
                    "scheduler_id": "boefje-test",
                    "type": "boefje",
                    "p_item": {
                        "id": "2e757dd3-66c7-46b8-9987-7cd18252cc6d",
                        "scheduler_id": "boefje-test",
                        "hash": "416aa907e0b2a16c1b324f7d3261c5a4",
                        "priority": 631,
                        "data": {
                            "id": "2e757dd366c746b899877cd18252cc6d",
                            "boefje": {"id": "test-plugin", "version": None},
                            "input_ooi": "Hostname|internet|example.com",
                            "organization": "test",
                            "dispatches": [],
                        },
                        "created_at": "2023-05-09T09:37:20.899668+00:00",
                        "modified_at": "2023-05-09T09:37:20.899675+00:00",
                    },
                    "status": "completed",
                    "created_at": "2023-05-09T09:37:20.909069+00:00",
                    "modified_at": "2023-05-09T09:37:20.909071+00:00",
                }
            ],
        }
    )

    mock_scheduler_client_session.get.return_value = scheduler_return_value

    request = setup_request(rf.get("plugin_detail"), superuser_member.user)
    response = PluginDetailView.as_view()(
        request,
        organization_code=superuser_member.organization.code,
        plugin_id="test-plugin",
    )

    assert response.status_code == 200

    assertContains(response, "TestBoefje")
    assertContains(response, "Completed")
