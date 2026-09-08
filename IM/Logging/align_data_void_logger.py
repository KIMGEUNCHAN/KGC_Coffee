"""Safe Void GOOD/NG updates for AlignData.csv.

AlignData.csv is an alignment-offset contract file.
Do not FileMode.Create it from the void path, do not append extra
align rows, and do not write GOOD/NG into OffsetX/Y.
Only refresh a trailing VoidResult column on existing rows.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path

VOID_COLUMN = "VoidResult"
GOOD = "GOOD"
NG = "NG"
_lock = threading.Lock()


def normalize_judge(judge: str | None) -> str:
    text = (judge or "").strip().upper()
    if text in {"OK", "PASS", "GOOD", "G"}:
        return GOOD
    if text in {"NG", "FAIL", "NOGOOD", "N"}:
        return NG
    return text


def write_die_result(csv_path: str | os.PathLike[str], die_key: str, judge: str, key_column_index: int = 0) -> None:
    path = str(csv_path)
    verdict = _require_judge(judge)
    with _lock:
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
