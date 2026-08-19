import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from IM.Logging.lot_boundary_logger import (  # noqa: E402
    LAST_FILE_NAME,
    begin_lot,
    daily_directory,
    daily_path,
    end_lot,
    last_path,
    reset_for_tests,
    set_log_root,
    write,
)


class LotBoundaryLoggerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        set_log_root(self._tmp.name)
        reset_for_tests()

    def tearDown(self):
        reset_for_tests()
        self._tmp.cleanup()

    def test_last_is_at_log_root_not_inside_date_folder(self):
        begin_lot("LOT-1")
        write("ALIGN OK")

        last = Path(last_path())
        dated_last = Path(daily_directory()) / LAST_FILE_NAME

        self.assertEqual(last.name, "LotBoundary_LAST.txt")
        self.assertEqual(last.parent, Path(self._tmp.name))
        self.assertTrue(last.is_file(), "LAST must be created immediately")
        self.assertFalse(
            dated_last.exists(),
            "LAST must not be written under the dated folder",
        )

    def test_daily_file_is_under_date_folder(self):
        write("STEP 1")
        daily = Path(daily_path())
        self.assertTrue(daily.is_file())
        self.assertEqual(daily.parent, Path(daily_directory()))
        self.assertTrue(daily.name.startswith("LotBoundary_"))
        self.assertTrue(daily.name.endswith(".txt"))

    def test_stage_lines_are_on_disk_immediately(self):
        begin_lot("LOT-2")
        write("STAGE A")

        last_text = Path(last_path()).read_text(encoding="utf-8")
        daily_text = Path(daily_path()).read_text(encoding="utf-8")

        self.assertIn("LotBoundary START lot=LOT-2", last_text)
        self.assertIn("STAGE A", last_text)
        self.assertIn("STAGE A", daily_text)
        self.assertGreater(Path(last_path()).stat().st_size, 0)

    def test_last_is_current_lot_only_daily_keeps_history(self):
        begin_lot("LOT-A")
        write("A1")
        begin_lot("LOT-B")
        write("B1")
        end_lot("LOT-B", "OK")

        last_text = Path(last_path()).read_text(encoding="utf-8")
        daily_text = Path(daily_path()).read_text(encoding="utf-8")

        self.assertNotIn("LOT-A", last_text)
        self.assertNotIn("A1", last_text)
        self.assertIn("LOT-B", last_text)
        self.assertIn("B1", last_text)
        self.assertIn("result=OK", last_text)

        self.assertIn("LOT-A", daily_text)
        self.assertIn("A1", daily_text)
        self.assertIn("LOT-B", daily_text)

    def test_no_leftover_tmp_after_flush(self):
        write("FLUSH")
        leftovers = list(Path(self._tmp.name).glob("*.tmp"))
        self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
