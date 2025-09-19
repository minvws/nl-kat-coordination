import pytest

from files.models import File
from plugins.models import Plugin
from plugins.runner import PluginRunner


@pytest.mark.django_db(transaction=True)
def test_hello_world():
    plugin = Plugin.objects.create(
        name="testing plugins", plugin_id="test", oci_image="hello-world:linux", oci_arguments=["/hello"]
    )

    hello_world = PluginRunner().run(plugin.plugin_id, None, output="-")
    assert "Hello from Docker!" in hello_world

    assert File.objects.count() == 0

    new_out = PluginRunner().run(plugin.plugin_id, None)
    assert "Upload completed. Server responded with: 201 Created" in new_out

    assert File.objects.count() == 1
    file = File.objects.first()
    assert file.file.read().decode() == hello_world
