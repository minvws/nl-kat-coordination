from pathlib import Path
from unittest import TestCase

from pydantic import BaseModel

import keiko.templates
from keiko.templates import get_templates, get_data_shape, get_samples


class KeikoTemplatesTest(TestCase):
    def setUp(self) -> None:
        self.maxDiff = None
        keiko.templates.settings.templates_folder = Path(__file__).parent / "fixtures" / "templates"

    def test_list_templates(self):
        templates = get_templates()
        self.assertEqual(templates, {"template1", "template2"})

    def test_get_data_shape(self):
        shape: BaseModel = get_data_shape("template1")

        self.assertEqual(shape.__name__, "DataShape")
        self.assertEqual(
            shape.__fields__["models"].type_.__fields__["sub_model"].type_.__fields__["prop2"].type_,
            int,
        )

    def test_get_samples(self):
        samples = get_samples()
        self.assertDictEqual(
            {
                "summary": "template2",
                "value": {
                    "template": "intel",
                    "data": {"findings": {}, "finding_types": {}},
                    "glossary": "test.glossary.csv",
                },
            },
            samples["template2"],
        )

    def test_get_samples_error(self):
        keiko.templates.settings.templates_folder = "gibberish"
        with self.assertRaises(FileNotFoundError):
            get_samples()
