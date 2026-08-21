import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from IM.Keys.aoi_keys import (  # noqa: E402
    AOI_ACTIONS,
    CLASS_ACTIONS,
    DEFAULT_BINDINGS,
    KEY_CODES,
    MOD_CONTROL,
    bind,
    bind_class,
    class_no_from_action,
    config_path,
    current_bindings,
    daily_directory,
    daily_path,
    key_name,
    last_path,
    load,
    parse_key,
    process_key,
    reset_for_tests,
    save_default,
    set_config_path,
    set_log_root,
    try_get_action,
    write_key_log,
)


class AOIKeysTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        set_log_root(self.root / "Log")
        set_config_path(self.root / "Config" / "AOIKeys.ini")
        reset_for_tests()

    def tearDown(self):
        reset_for_tests()
        self._tmp.cleanup()

    def test_default_function_keys(self):
        self.assertEqual(try_get_action("F5"), "Start")
        self.assertEqual(try_get_action("Escape"), "Stop")
        self.assertEqual(try_get_action("Esc"), "Stop")
        self.assertEqual(try_get_action("F6"), "Pause")
        self.assertEqual(try_get_action("F4"), "Auto")
        self.assertEqual(try_get_action("F3"), "Manual")
        self.assertEqual(try_get_action("F2"), "Grab")
        self.assertEqual(try_get_action("F1"), "Live")
        self.assertEqual(try_get_action("F9"), "Save")
        self.assertEqual(try_get_action("F10"), "Recipe")

    def test_judgment_and_map_keys(self):
        self.assertEqual(try_get_action("Enter"), "OK")
        self.assertEqual(try_get_action("Return"), "OK")
        self.assertEqual(try_get_action("Space"), "NG")
        self.assertEqual(try_get_action("R"), "Retry")
        self.assertEqual(try_get_action("S"), "Skip")
        self.assertEqual(try_get_action("Right"), "Next")
        self.assertEqual(try_get_action("Left"), "Prev")
        self.assertEqual(try_get_action("Down"), "NextRow")
        self.assertEqual(try_get_action("Up"), "PrevRow")
        self.assertEqual(try_get_action("Home"), "Home")
        self.assertEqual(try_get_action("A"), "Align")

    def test_class_keys_from_digit_and_numpad(self):
        for n in range(1, 10):
            self.assertEqual(try_get_action(f"D{n}"), f"Class{n}")
            self.assertEqual(try_get_action(f"NumPad{n}"), f"Class{n}")
            self.assertEqual(try_get_action(str(n)), f"Class{n}")
            self.assertEqual(class_no_from_action(f"Class{n}"), n)

    def test_class_no_from_unrelated_action_is_none(self):
        self.assertIsNone(class_no_from_action("Start"))
        self.assertIsNone(class_no_from_action(""))
        self.assertIsNone(class_no_from_action(None))
        self.assertIsNone(class_no_from_action("Class0"))
        self.assertIsNone(class_no_from_action("Class10"))

    def test_parse_key_matches_winforms_codes(self):
        self.assertEqual(parse_key("F5"), 116)
        self.assertEqual(parse_key("Enter"), 13)
        self.assertEqual(parse_key("Escape"), 27)
        self.assertEqual(parse_key("D1"), 49)
        self.assertEqual(parse_key("NumPad1"), 97)
        self.assertEqual(parse_key("Ctrl+F5"), MOD_CONTROL | 116)
        self.assertEqual(parse_key("Control+F5"), MOD_CONTROL | 116)
        self.assertEqual(key_name(MOD_CONTROL | 116), "Ctrl+F5")
        self.assertEqual(key_name("f5"), "F5")

    def test_unknown_key_returns_none(self):
        self.assertIsNone(try_get_action("F12"))
        self.assertIsNone(try_get_action("Ctrl+F5"))
        self.assertIsNone(process_key("F12"))
        self.assertFalse(Path(last_path()).exists())

    def test_bind_override_and_bind_class(self):
        bind("Start", "F8")
        self.assertEqual(try_get_action("F8"), "Start")
        self.assertIsNone(try_get_action("F5"))

        bind_class(3, "Q")
        self.assertEqual(try_get_action("Q"), "Class3")
        self.assertIsNone(try_get_action("D3"))
        self.assertEqual(class_no_from_action(try_get_action("Q")), 3)

    def test_load_ini_overlay_and_comments(self):
        ini = self.root / "Config" / "AOIKeys.ini"
        ini.parent.mkdir(parents=True)
        ini.write_text(
            "; comment\n"
            "# hash comment\n"
            "[AOIKeys]\n"
            "Start=F8\n"
            "Stop=Q\n"
            "Class1=F11\n"
            "[Other]\n"
            "Start=F1\n",
            encoding="utf-8",
        )

        loaded = load(ini)
        self.assertEqual(loaded["Start"], "F8")
        self.assertEqual(try_get_action("F8"), "Start")
        self.assertEqual(try_get_action("Q"), "Stop")
        self.assertEqual(try_get_action("F11"), "Class1")
        self.assertIsNone(try_get_action("F5"))
        self.assertIsNone(try_get_action("Escape"))
        self.assertEqual(try_get_action("F2"), "Grab")

    def test_load_bundled_ini_keeps_all_default_actions(self):
        bundled = ROOT / "IM" / "Keys" / "AOIKeys.ini"
        loaded = load(bundled)
        for action in AOI_ACTIONS:
            self.assertIn(action, loaded)
            self.assertEqual(loaded[action].replace(" ", ""), DEFAULT_BINDINGS[action].replace(" ", ""))
        self.assertEqual(len(CLASS_ACTIONS), 9)
        self.assertEqual(try_get_action("F5"), "Start")
        self.assertEqual(try_get_action("NumPad9"), "Class9")

    def test_save_default_creates_config_folder(self):
        dest = self.root / "Config" / "AOIKeys.ini"
        self.assertFalse(dest.exists())
        saved = Path(save_default())
        self.assertEqual(saved, dest)
        self.assertTrue(dest.is_file())
        text = dest.read_text(encoding="utf-8")
        self.assertIn("[AOIKeys]", text)
        self.assertIn("Start=F5", text)
        self.assertIn("Class9=D9,NumPad9", text)
        self.assertEqual(try_get_action("F5"), "Start")

    def test_process_key_writes_last_and_daily_immediately(self):
        action = process_key("F5")
        self.assertEqual(action, "Start")

        last = Path(last_path())
        daily = Path(daily_path())
        dated_last = Path(daily_directory()) / "AOIKeys_LAST.txt"

        self.assertTrue(last.is_file())
        self.assertTrue(daily.is_file())
        self.assertEqual(last.parent, Path(self.root / "Log"))
        self.assertEqual(daily.parent, Path(daily_directory()))
        self.assertFalse(dated_last.exists())

        last_text = last.read_text(encoding="utf-8")
        daily_text = daily.read_text(encoding="utf-8")
        self.assertIn("Action=Start", last_text)
        self.assertIn("Key=F5", last_text)
        self.assertIn(" : ", last_text)
        self.assertIn("Action=Start", daily_text)
        self.assertGreater(last.stat().st_size, 0)

    def test_try_get_action_does_not_write_log(self):
        self.assertEqual(try_get_action("F5"), "Start")
        self.assertFalse(Path(last_path()).exists())
        self.assertFalse(Path(daily_path()).exists())

    def test_write_key_log_reuses_existing_date_folder(self):
        from datetime import datetime

        stamp = datetime.now().strftime("%Y-%m-%d")
        existing = self.root / "Log" / stamp
        existing.mkdir(parents=True)
        write_key_log("Align", "A")
        self.assertTrue((existing / f"AOIKeys_{stamp}.txt").is_file())
        self.assertTrue(Path(last_path()).is_file())

    def test_process_key_accepts_winforms_int(self):
        self.assertEqual(process_key(KEY_CODES["F5"]), "Start")
        self.assertEqual(process_key(KEY_CODES["NUMPAD3"]), "Class3")
        bind("Start", "Ctrl+F5")
        self.assertEqual(process_key(MOD_CONTROL | KEY_CODES["F5"]), "Start")
        self.assertIsNone(process_key(KEY_CODES["F5"]))

    def test_config_path_follows_set_config_path(self):
        dest = self.root / "other" / "keys.ini"
        set_config_path(dest)
        self.assertEqual(Path(config_path()), dest)

    def test_current_bindings_roundtrip_names(self):
        names = current_bindings()
        self.assertEqual(names["Start"], "F5")
        self.assertEqual(names["Class1"], "D1,NumPad1")
        self.assertEqual(names["OK"], "Enter")


if __name__ == "__main__":
    unittest.main()
