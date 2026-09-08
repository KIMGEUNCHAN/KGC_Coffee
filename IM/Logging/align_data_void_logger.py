"""Always save AlignData.csv for Void GOOD and NG.

Shop-floor bug:
    if good:
        save AlignData.csv
    # NG skips save, so the csv only ever contains GOOD.

SaveAfterVoidInspect writes GOOD and NG. Call it before the NG popup.
If the csv is missing (because the Good-only guard skipped it), still
create the file so NG is visible. Pass in-memory align rows when you
have them so offsets are not lost on NG.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path

VOID_COLUMN = "VoidResult"
GOOD = "GOOD"
NG = "NG"
DEFAULT_HEADER = ["No", "PosX", "PosY", "OffsetX", "OffsetY", "Score", "Result", VOID_COLUMN]
_lock = threading.Lock()


def normalize_judge(judge: str | None) -> str:
    text = (judge or "").strip().upper()
    if text in {"OK", "PASS", "GOOD", "G"}:
        return GOOD
    if text in {"NG", "FAIL", "NOGOOD", "N"}:
        return NG
    return text


def must_save_align_data(judge: str | None) -> bool:
    """NG must save too. A Good-only guard is the contradiction."""
    return normalize_judge(judge) in {GOOD, NG}


def save_after_void_inspect(
    csv_path: str | os.PathLike[str],
    die_key: str,
    judge: str,
    header: list[str] | None = None,
    rows: list[list[str]] | None = None,
) -> None:
    """Persist Void GOOD/NG before the NG popup. Never skip save on NG."""
    path = str(csv_path)
    verdict = _require_judge(judge)
    with _lock:
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            _write_die_result_locked(path, die_key, verdict, 0)
            return
        table = _from_snapshot(header, rows, die_key, verdict)
        table.save(path)


def write_die_result(csv_path: str | os.PathLike[str], die_key: str, judge: str, key_column_index: int = 0) -> None:
    path = str(csv_path)
    verdict = _require_judge(judge)
    with _lock:
        _write_die_result_locked(path, die_key, verdict, key_column_index)


def _write_die_result_locked(path: str, die_key: str, verdict: str, key_column_index: int) -> None:
    table = _load(path)
    table.ensure_void_column()
    key_col = table.find_key_column(key_column_index)
    void_col = table.void_column_index()
    hit = False
    for row in table.rows:
        if len(row) > key_col and row[key_col].strip().lower() == str(die_key).strip().lower():
            table.set_cell(row, void_col, verdict)
            hit = True
    if not hit:
        raise LookupError(
            f"AlignData row not found for die {die_key}. Do not append a new align row."
        )
    table.save(path)


def write_wafer_result(csv_path: str | os.PathLike[str], judge: str) -> None:
    path = str(csv_path)
    verdict = _require_judge(judge)
    with _lock:
        table = _load(path)
        table.ensure_void_column()
        void_col = table.void_column_index()
        for row in table.rows:
            table.set_cell(row, void_col, verdict)
        table.save(path)


def _require_judge(judge: str) -> str:
    verdict = normalize_judge(judge)
    if verdict not in {GOOD, NG}:
        raise ValueError("judge must be GOOD or NG")
    return verdict


class _CsvTable:
    def __init__(self, header: list[str], rows: list[list[str]], has_header: bool) -> None:
        self.header = header
        self.rows = rows
        self.has_header = has_header

    def save(self, path: str) -> None:
        lines: list[str] = []
        if self.has_header:
            lines.append(",".join(self.header))
        lines.extend(",".join(row) for row in self.rows)
        text = "\r\n".join(lines) + "\r\n"
        tmp = path + ".voidtmp"
        Path(tmp).write_bytes(text.encode("utf-8"))
        os.replace(tmp, path)

    def ensure_void_column(self) -> None:
        if self.has_header and VOID_COLUMN not in self.header:
            self.header.append(VOID_COLUMN)
        need = self.column_count()
        for row in self.rows:
            while len(row) < need:
                row.append("")

    def void_column_index(self) -> int:
        if self.has_header and VOID_COLUMN in self.header:
            return self.header.index(VOID_COLUMN)
        return self.column_count() - 1

    def find_key_column(self, fallback_index: int) -> int:
        if self.has_header:
            for name in ("No", "Die", "Index", "DieNo", "Site", "ID"):
                for i, col in enumerate(self.header):
                    if col.strip().lower() == name.lower():
                        return i
        return max(fallback_index, 0)

    def set_cell(self, row: list[str], col: int, value: str) -> None:
        while len(row) <= col:
            row.append("")
        row[col] = value

    def column_count(self) -> int:
        n = len(self.header) if self.has_header else 0
        for row in self.rows:
            n = max(n, len(row))
        return max(n, 1)


def _load(path: str) -> _CsvTable:
    if not os.path.isfile(path):
        raise FileNotFoundError(
            "AlignData.csv not found. Write void result only after Align has created the file."
        )
    raw = Path(path).read_bytes().decode("utf-8", errors="replace")
    lines = [line for line in raw.replace("\r\n", "\n").replace("\r", "\n").split("\n") if line != ""]
    if not lines:
        raise ValueError("AlignData.csv is empty. Do not FileMode.Create.")
    first = lines[0].split(",")
    has_header = _looks_like_header(first)
    header = first if has_header else []
    start = 1 if has_header else 0
    rows = [line.split(",") for line in lines[start:]]
    return _CsvTable(header, rows, has_header)


def _from_snapshot(
    header: list[str] | None,
    rows: list[list[str]] | None,
    die_key: str,
    verdict: str,
) -> _CsvTable:
    use_header = list(header) if header else list(DEFAULT_HEADER)
    table = _CsvTable(use_header, [list(row) for row in rows] if rows else [], True)
    if not table.rows:
        table.rows = [[""] * len(table.header)]
        table.rows[0][0] = str(die_key)
    table.ensure_void_column()
    key_col = table.find_key_column(0)
    void_col = table.void_column_index()
    hit = False
    for row in table.rows:
        if len(row) > key_col and row[key_col].strip().lower() == str(die_key).strip().lower():
            table.set_cell(row, void_col, verdict)
            hit = True
    if not hit and table.rows:
        table.set_cell(table.rows[0], void_col, verdict)
        if len(table.rows[0]) > key_col:
            table.rows[0][key_col] = str(die_key)
    return table


def _looks_like_header(cells: list[str]) -> bool:
    if not cells:
        return False
    for cell in cells:
        text = cell.strip()
        if not text:
            continue
        try:
            float(text)
            return False
        except ValueError:
            pass
    head = cells[0].strip().lower()
    if head in {"no", "die"} or "offset" in head or "pos" in head:
        return True
    return len(cells) >= 2
