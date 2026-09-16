import os
import tempfile
import unittest
from pathlib import Path

from alpha_lab_os.config import load_local_env


class ConfigTests(unittest.TestCase):
    def test_env_file_does_not_overwrite_process_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("ALPHA_LAB_TEST=from-file\n", encoding="utf-8")
            os.environ["ALPHA_LAB_TEST"] = "from-process"
            load_local_env(str(path))
            self.assertEqual(os.environ["ALPHA_LAB_TEST"], "from-process")

