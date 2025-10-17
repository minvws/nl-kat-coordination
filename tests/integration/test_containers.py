import pytest
from django.core.files.base import ContentFile

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


# todo: todo and fix everything below


@pytest.mark.django_db(transaction=True)
def test_input_output():
    plugin = Plugin.objects.create(
        name="Test Plugin", plugin_id="cat-plugin", oci_image="alpine:latest", oci_arguments=["/bin/cat"]
    )

    output = PluginRunner().run(plugin.plugin_id, "hello world^C", output="-")
    assert output == "hello world^C"
    assert File.objects.count() == 0


# test write to stdout
# - also results in 1 (temp) file


@pytest.mark.django_db(transaction=True)
def test_with_static_file_input():
    file = File.objects.create(file=ContentFile("test content", "test.txt"), type="txt")
    plugin = Plugin.objects.create(
        name="Cat File Plugin",
        plugin_id="cat-file-plugin",
        oci_image="alpine:latest",
        oci_arguments=["/bin/cat", "{file/" + str(file.pk) + "}"],
    )

    output = PluginRunner().run(plugin.plugin_id, None, output="-")
    assert output == "test content"


@pytest.mark.django_db(transaction=True)
def test_with_argument():
    plugin = Plugin.objects.create(
        name="DNS Plugin",
        plugin_id="nslookup-plugin",
        oci_image="alpine:latest",
        oci_arguments=["nslookup", "{hostname}"],
    )

    output = PluginRunner().run(plugin.plugin_id, ["nu.nl"], output="-")
    assert "Name:	nu.nl" in output


@pytest.mark.django_db(transaction=True)
def test_with_multiple_arguments():
    plugin = Plugin.objects.create(
        name="DNS Plugin",
        plugin_id="nslookup-plugin",
        oci_image="alpine:latest",
        oci_arguments=["nslookup", "{hostname}"],
    )
    output = PluginRunner().run(plugin.plugin_id, ["nu.nl", "example.com"], output="-")
    assert "Name:	nu.nl" in output
    assert "Name:	example.com" in output


# test with file input ("{file"})
# - create File with pk = 123
# - oci_arguments: "{file/<file.pk>}"
# - run(plugin id, target=None, output="-")

# test with single argument
# - create plugin, with oci_arguments ['curl', 'http://..'] and oci_image=alpine

# test with variable argument
# alpine:latest
# args: ['nslookup', '{hostname}'
# run(plugin id, target=['example.com'], output='-')

# test above with multiple inputs
# run(plugin id, target=['example.com', 'test.com'], output='-')


# alpine:
# ["xargs", "-I", "{}", "-P", "4",  "nslookup", "{}"]
#
# 11:36
#
#
#
# x6019 says:Dan ["example.xom", "
# test.com
# "]
#
# 11:37
#
# x6019 says:
# example.com
#
# test.com
#
