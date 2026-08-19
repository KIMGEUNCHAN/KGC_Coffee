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
    ensure_directories,
    last_path,
    recover_last_from_dated_logs,
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

    def test_missing_folders_are_created_automatically(self):
        nested = Path(self._tmp.name) / "not-created-yet" / "Log"
        self.assertFalse(nested.exists())
        set_log_root(nested)

        write("AUTO MKDIR")

        self.assertTrue(nested.is_dir())
        self.assertTrue(Path(daily_directory()).is_dir())
        self.assertTrue(Path(last_path()).is_file())
        self.assertTrue(Path(daily_path()).is_file())

    def test_ensure_directories_creates_folders_without_writing_files(self):
        nested = Path(self._tmp.name) / "startup" / "Log"
        set_log_root(nested)

        ensure_directories()

        self.assertTrue(nested.is_dir())
        self.assertTrue(Path(daily_directory()).is_dir())
        self.assertFalse(Path(last_path()).exists())

    def test_recover_last_from_date_folder_last_file(self):
        dated_last = Path(daily_directory()) / LAST_FILE_NAME
        dated_last.parent.mkdir(parents=True)
        dated_last.write_text("from-date-folder\n", encoding="utf-8")

        self.assertFalse(Path(last_path()).exists())
        self.assertTrue(recover_last_from_dated_logs())
        self.assertEqual(Path(last_path()).read_text(encoding="utf-8"), "from-date-folder\n")

    def test_recover_last_from_daily_lotboundary_log(self):
        daily = Path(daily_path())
        daily.parent.mkdir(parents=True)
        daily.write_text("daily-lotboundary\n", encoding="utf-8")

        self.assertTrue(recover_last_from_dated_logs())
        self.assertEqual(Path(last_path()).read_text(encoding="utf-8"), "daily-lotboundary\n")

    def test_write_puts_last_at_root_even_if_other_logs_already_exist(self):
        other = Path(daily_directory()) / "Inspect_20260819.txt"
        other.parent.mkdir(parents=True)
        other.write_text("other module\n", encoding="utf-8")

        write("LOTBOUNDARY STAGE")

        self.assertTrue(Path(last_path()).is_file())
        self.assertIn("LOTBOUNDARY STAGE", Path(last_path()).read_text(encoding="utf-8"))
        self.assertFalse((Path(daily_directory()) / LAST_FILE_NAME).exists())


if __name__ == "__main__":
    unittest.main()
