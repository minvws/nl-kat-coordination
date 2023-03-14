from pathlib import Path
from unittest import TestCase

from keiko.keiko import read_glossary
from keiko.settings import Settings


class KeikoGlossaryTest(TestCase):
    def setUp(self) -> None:
        self.maxDiff = None
        self.settings = Settings(glossaries_folder=str(Path(__file__).parent / "fixtures" / "glossaries"))

    def test_read_glossary(self):
        glossary_entries = read_glossary("test_glossary.csv", self.settings)
        self.assertEqual({"meow": ("Meow", "The sound a cat makes when hungry")}, glossary_entries)
