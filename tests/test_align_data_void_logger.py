from __future__ import annotations

from pathlib import Path

import pytest

from IM.Logging.align_data_void_logger import (
    VOID_COLUMN,
    must_save_align_data,
    save_after_void_inspect,
    write_die_result,
    write_wafer_result,
)

HEADER = "No,PosX,PosY,OffsetX,OffsetY,Score,Result"
ROW1 = "1,10.0,20.0,0.012,-0.008,98.5,OK"
ROW2 = "2,10.0,40.0,-0.004,0.021,97.1,OK"


def _write_align(path: Path, text: str) -> Path:
    path.write_text(text.replace("\n", "\r\n"), encoding="utf-8")
    return path


def test_void_ng_keeps_offset_columns(tmp_path: Path) -> None:
    csv = _write_align(tmp_path / "AlignData.csv", f"{HEADER}\n{ROW1}\n{ROW2}\n")
    write_die_result(csv, "2", "NG")

    lines = csv.read_text(encoding="utf-8").strip().splitlines()
    assert lines[0].endswith("," + VOID_COLUMN)
    assert "0.012" in lines[1]
    assert "-0.008" in lines[1]
    assert lines[1].endswith(",")
    assert lines[2].endswith(",NG")
    assert lines[2].split(",")[6] == "OK"
    assert len(lines) == 3


def test_unknown_die_does_not_append_align_row(tmp_path: Path) -> None:
    csv = _write_align(tmp_path / "AlignData.csv", f"{HEADER}\n{ROW1}\n")
    with pytest.raises(LookupError, match="Do not append"):
        write_die_result(csv, "99", "NG")
    text = csv.read_text(encoding="utf-8")
    assert "99" not in text
    assert VOID_COLUMN not in text
    assert len(text.strip().splitlines()) == 2


def test_create_only_void_file_would_drop_offsets(tmp_path: Path) -> None:
    csv = tmp_path / "AlignData.csv"
    csv.write_text("GOOD\n", encoding="utf-8")
    with pytest.raises((ValueError, FileNotFoundError, LookupError)):
        write_die_result(csv, "1", "GOOD")


def test_missing_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="after Align"):
        write_die_result(tmp_path / "AlignData.csv", "1", "NG")


def test_wafer_result_does_not_add_rows(tmp_path: Path) -> None:
    csv = _write_align(tmp_path / "AlignData.csv", f"{HEADER}\n{ROW1}\n{ROW2}\n")
    write_wafer_result(csv, "ok")
    lines = csv.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3
    assert lines[1].endswith(",GOOD")
    assert lines[2].endswith(",GOOD")
    assert lines[1].split(",")[3] == "0.012"


def test_retry_overwrites_same_die_void_cell(tmp_path: Path) -> None:
    csv = _write_align(tmp_path / "AlignData.csv", f"{HEADER}\n{ROW1}\n")
    write_die_result(csv, "1", "NG")
    write_die_result(csv, "1", "GOOD")
    lines = csv.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert lines[1].endswith(",GOOD")
    assert ",NG" not in lines[1]


def test_must_save_align_data_for_ng_and_good() -> None:
    assert must_save_align_data("GOOD") is True
    assert must_save_align_data("NG") is True
    assert must_save_align_data("ok") is True
    assert must_save_align_data("fail") is True
    assert must_save_align_data("skip") is False


def test_good_only_guard_hides_ng(tmp_path: Path) -> None:
    csv = tmp_path / "AlignData.csv"

    def old_save(judge: str) -> None:
        if judge != "GOOD":
            return
        save_after_void_inspect(csv, "1", judge)

    old_save("NG")
    assert not csv.exists()
    old_save("GOOD")
    assert "GOOD" in csv.read_text(encoding="utf-8")
    assert "NG" not in csv.read_text(encoding="utf-8")


def test_ng_is_saved_when_file_is_missing(tmp_path: Path) -> None:
    csv = tmp_path / "AlignData.csv"
    save_after_void_inspect(csv, "2", "NG")
    text = csv.read_text(encoding="utf-8")
    assert csv.exists()
    assert "NG" in text
    assert VOID_COLUMN in text
    assert "2" in text


def test_ng_keeps_in_memory_offsets_when_good_guard_skipped_file(tmp_path: Path) -> None:
    csv = tmp_path / "AlignData.csv"
    header = HEADER.split(",")
    rows = [ROW2.split(",")]
    save_after_void_inspect(csv, "2", "NG", header=header, rows=rows)
    lines = csv.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert lines[1].split(",")[3] == "-0.004"
    assert lines[1].endswith(",NG")
    assert lines[1].split(",")[6] == "OK"


def test_save_after_void_updates_existing_csv_on_ng(tmp_path: Path) -> None:
    csv = _write_align(tmp_path / "AlignData.csv", f"{HEADER}\n{ROW1}\n{ROW2}\n")
    save_after_void_inspect(csv, "1", "NG")
    save_after_void_inspect(csv, "2", "GOOD")
    lines = csv.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3
    assert lines[1].endswith(",NG")
    assert lines[2].endswith(",GOOD")
    assert lines[1].split(",")[3] == "0.012"
