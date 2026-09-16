import tempfile
import unittest
from pathlib import Path

from alpha_lab_os.demo import seed_demo
from alpha_lab_os.storage import Store


class StorageTests(unittest.TestCase):
    def test_demo_is_append_only_and_queryable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "demo.db"
            counts = seed_demo(path, periods=3, tokens=3)
            self.assertEqual(counts["market_state"], 9)
            self.assertEqual(counts["quotes"], 9)
            with Store(path) as store:
                self.assertEqual(len(store.panel_rows()), 9)
                self.assertEqual(store.counts()["market_state"], 9)

