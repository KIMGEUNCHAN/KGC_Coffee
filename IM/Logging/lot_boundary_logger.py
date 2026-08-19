"""WISVision-style log writer.

Same calling shape as the existing equipment logger:

    write_log("Inspect", "Align OK")
    write_log("LotBoundary", "FindEdge OK")

Files:
    {root}/{Name}_LAST.txt
    {root}/{date}/{Name}_{date}.txt
"""

from __future__ import annotations

import os
import threading
from datetime import datetime

DEFAULT_LOG_ROOT = r"C:\WISVision\Log"
DATE_FORMAT = "%Y%m%d"
DATE_FORMATS = ("%Y%m%d", "%Y-%m-%d", "%Y_%m_%d")
MODULE_LOTBOUNDARY = "LotBoundary"

_lock = threading.Lock()
_log_root = DEFAULT_LOG_ROOT


def set_log_root(path: str | os.PathLike[str]) -> None:
    global _log_root
    _log_root = str(path)


def log_root() -> str:
    return _log_root


def date_stamp(now: datetime | None = None) -> str:
    now = now or datetime.now()
    for fmt in DATE_FORMATS:
        stamp = now.strftime(fmt)
        if os.path.isdir(os.path.join(_log_root, stamp)):
            return stamp
    return now.strftime(DATE_FORMAT)


def daily_directory(now: datetime | None = None) -> str:
    now = now or datetime.now()
    return os.path.join(_log_root, date_stamp(now))


def daily_path(name: str = MODULE_LOTBOUNDARY, now: datetime | None = None) -> str:
    now = now or datetime.now()
    date = date_stamp(now)
    return os.path.join(daily_directory(now), f"{name}_{date}.txt")


def last_path(name: str = MODULE_LOTBOUNDARY) -> str:
    return os.path.join(_log_root, f"{name}_LAST.txt")


def write_log(str_name: str, str_log: str | None, b_new_last: bool = False) -> None:
    """Mirror of clsLog.WriteLog(strName, strLog, bNewLast)."""
    name = str_name or "System"
    msg = str_log or ""
    now = datetime.now()
    line = f"{now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} : {msg}\n"

    with _lock:
        os.makedirs(_log_root, exist_ok=True)
        os.makedirs(daily_directory(now), exist_ok=True)
        _write_line_flush(last_path(name), line, b_new_last)
        _write_line_flush(daily_path(name, now), line, False)


def begin_lot(lot_id: str | None) -> None:
    write_log(MODULE_LOTBOUNDARY, f"Lot Start : {lot_id or ''}", True)


def end_lot(lot_id: str | None, result: str | None) -> None:
    write_log(MODULE_LOTBOUNDARY, f"Lot End : {lot_id or ''} Result={result or ''}")


def write(message: str | None) -> None:
    write_log(MODULE_LOTBOUNDARY, message)


def _write_line_flush(path: str, text: str, new_file: bool) -> None:
    flags = os.O_WRONLY | os.O_CREAT
    if new_file or not os.path.isfile(path):
        flags |= os.O_TRUNC
    else:
        flags |= os.O_APPEND
    fd = os.open(path, flags, 0o644)
    try:
        os.write(fd, text.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


# Compatibility names used by older tests
LAST_FILE_NAME = f"{MODULE_LOTBOUNDARY}_LAST.txt"


def ensure_directories(now: datetime | None = None) -> None:
    os.makedirs(_log_root, exist_ok=True)
    os.makedirs(daily_directory(now), exist_ok=True)


def recover_last_from_dated_logs() -> bool:
    if os.path.isfile(last_path()):
        return False
    dated_last = os.path.join(daily_directory(), LAST_FILE_NAME)
    if _copy_if_exists(dated_last, last_path()):
        return True
    if _copy_if_exists(daily_path(), last_path()):
        return True
    return False


def reset_for_tests() -> None:
    return


def _copy_if_exists(source: str | None, destination: str) -> bool:
    if not source or not os.path.isfile(source):
        return False
    if os.path.abspath(source) == os.path.abspath(destination):
        return False
    with open(source, "rb") as src:
        data = src.read()
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    return True
