import zipfile
from django.test import SimpleTestCase

from rocky.views import zip_data


class ZipTestCase(SimpleTestCase):
    def test_zip_data(self):
        data = b"1234"
        out_name = "test"

        z_file = zip_data(data, out_name, {})
        assert zipfile.is_zipfile(z_file)

        with zipfile.ZipFile(z_file, "r") as zf:
            assert zf.read(out_name) == data
