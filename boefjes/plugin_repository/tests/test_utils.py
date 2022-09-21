from unittest import TestCase

from boefjes.plugin_repository.tests.common import load_plugin
from boefjes.plugin_repository.models import Boefje, Image, File

EXAMPLE_BOEFJE_FILE = load_plugin("test-boefje.yml")


class TestUtils(TestCase):
    def setUp(self) -> None:
        self.example_config = EXAMPLE_BOEFJE_FILE
        self.example_image = Image(
            plugin=self.example_config, location="fixtures/test-boefje.yml"
        )

    def test_load_boefje(self):
        self.assertIsInstance(self.example_config, Boefje)

    def test_image_model_as_str(self):
        model = self.example_image

        self.assertEqual("kat-test-boefje", str(model))

    def test_image_model_alias(self):
        model = self.example_image

        self.assertEqual("kat-test-boefje/0.1-dev", model.alias)

    def test_image_model_aliases(self):
        model = self.example_image

        self.assertListEqual(["kat-test-boefje/0.1-dev"], model.aliases)

    def test_file_model_ftypes(self):
        pairs = [
            ("image/lxd.tar.xz", "lxd.tar.xz"),
            ("image/root.squashfs", "squashfs"),
            ("image/disk.qcow2", "disk-kvm.img"),
            ("image/root.20220130_23:08.vcdiff", "squashfs.vcdiff"),
            ("image/random-name", "random-name"),
        ]

        for path, ftype in pairs:
            with self.subTest(ftype=ftype):
                model = File(location=path, size=-1)
                self.assertEqual(ftype, model.ftype)
