from pathlib import Path
from unittest import TestCase

from keiko.keiko import settings, read_glossary


class KeikoGlossaryTest(TestCase):
    def setUp(self) -> None:
        self.maxDiff = None
        settings.glossaries_folder = Path(__file__).parent / "fixtures" / "glossaries"

    def test_read_glossary(self):
        glossary_entries = read_glossary("test_glossary.csv")
        self.assertEqual({"meow": ("Meow", "The sound a cat makes when hungry")}, glossary_entries)
