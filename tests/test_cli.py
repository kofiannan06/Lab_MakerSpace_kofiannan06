import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main


class CliSmokeTests(unittest.TestCase):
    def test_main_menu_can_exit_cleanly(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "cli_smoke.db"
            output = io.StringIO()

            with patch.object(main, "DEFAULT_DB_PATH", db_path), patch(
                "builtins.input", side_effect=["10"]
            ), patch("sys.stdout", output):
                main.main()

            self.assertIn("Safety-Focused Campus MakerSpace Checkout System", output.getvalue())
            self.assertIn("Goodbye.", output.getvalue())
            self.assertTrue(db_path.exists())


if __name__ == "__main__":
    unittest.main()
