import time
import unittest
from datetime import datetime, timedelta, timezone

from scheduler import utils


class ExpiringDictTestCase(unittest.TestCase):
    def test_lifetime_expired(self):
        ed = utils.ExpiringDict(lifetime=1, start_time=datetime.now(timezone.utc) - timedelta(seconds=2))
        ed["a"] = 1
        with self.assertRaises(utils.ExpiredError):
            ed.get("a")

        self.assertEqual(ed.cache, {})

        # Should not raise an error
        self.assertIsNone(ed.get("a"))

    def test_lifetime_not_expired(self):
        ed = utils.ExpiringDict()
        ed["a"] = 1

        self.assertEqual(1, ed.get("a"))
