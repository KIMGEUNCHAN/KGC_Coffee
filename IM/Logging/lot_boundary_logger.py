"""LotBoundary stage log with immediate disk flush.

Mirrors IM/Logging/LotBoundaryLogger.cs so LAST is written to the log root
(not the dated folder) and is readable right after each stage line.

    {root}/LotBoundary_LAST.txt
    {root}/{yyyyMMdd}/LotBoundary_{yyyyMMdd}.txt
"""

from __future__ import annotations

import os
import threading
from datetime import datetime

LAST_FILE_NAME = "LotBoundary_LAST.txt"
DATE_FORMAT = "%Y%m%d"
DATE_FORMATS = ("%Y%m%d", "%Y-%m-%d", "%Y_%m_%d")
DEFAULT_LOG_ROOT = r"C:\WISVision\Log"

_lock = threading.Lock()
_current_lot = []
_log_root = DEFAULT_LOG_ROOT


def set_log_root(path: str | os.PathLike[str]) -> None:
    global _log_root
    _log_root = str(path)


def log_root() -> str:
    return _log_root


def last_path() -> str:
    return os.path.join(_log_root, LAST_FILE_NAME)


def date_stamp(now: datetime | None = None) -> str:
    """Reuse the date folder WISVision already created, else yyyyMMdd."""
    now = now or datetime.now()
    for fmt in DATE_FORMATS:
        stamp = now.strftime(fmt)
        if os.path.isdir(os.path.join(_log_root, stamp)):
            return stamp
    return now.strftime(DATE_FORMAT)


def daily_directory(now: datetime | None = None) -> str:
    now = now or datetime.now()
    return os.path.join(_log_root, date_stamp(now))


def daily_path(now: datetime | None = None) -> str:
    now = now or datetime.now()
    date = date_stamp(now)
    return os.path.join(daily_directory(now), f"LotBoundary_{date}.txt")


def ensure_directories(now: datetime | None = None) -> None:
    """Create Log root and today's date folder. No-op if they already exist.

    If LotBoundary logs already exist only under a date folder, copy the newest
    one to {root}/LotBoundary_LAST.txt so LAST appears even when other WISVision
    logs are already being written.
    """
    os.makedirs(_log_root, exist_ok=True)
    os.makedirs(daily_directory(now), exist_ok=True)
    recover_last_from_dated_logs()


def recover_last_from_dated_logs() -> bool:
    """Copy a dated LotBoundary log up to the root LAST file if LAST is missing."""
    if os.path.isfile(last_path()):
        return False

    os.makedirs(_log_root, exist_ok=True)

    dated_last_today = os.path.join(daily_directory(), LAST_FILE_NAME)
    if _copy_if_exists(dated_last_today, last_path()):
        return True
    if _copy_if_exists(daily_path(), last_path()):
        return True

    newest = _find_newest_lotboundary_file()
    return _copy_if_exists(newest, last_path())


def begin_lot(lot_id: str | None) -> None:
    with _lock:
        _current_lot.clear()
        _write_unlocked(f"=== LotBoundary START lot={lot_id or ''} ===")


def end_lot(lot_id: str | None, result: str | None) -> None:
    write(f"=== LotBoundary END lot={lot_id or ''} result={result or ''} ===")


def write(message: str | None) -> None:
    with _lock:
        _write_unlocked(message)


def reset_for_tests() -> None:
    with _lock:
        _current_lot.clear()


def _write_unlocked(message: str | None) -> None:
    now = datetime.now()
    line = f"[{now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] {message or ''}\n"
    _current_lot.append(line)

    ensure_directories(now)

    _rewrite_and_flush(last_path(), "".join(_current_lot))
    _append_and_flush(daily_path(now), line)


def _append_and_flush(path: str, text: str) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, text.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


def _rewrite_and_flush(path: str, content: str) -> None:
    temp_path = path + ".tmp"
    fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        os.write(fd, content.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temp_path, path)


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


def _find_newest_lotboundary_file() -> str | None:
    newest = None
    newest_mtime = -1.0
    try:
        entries = os.listdir(_log_root)
    except OSError:
        return None

    for name in entries:
        folder = os.path.join(_log_root, name)
        if not os.path.isdir(folder):
            continue
        candidates = [os.path.join(folder, LAST_FILE_NAME)]
        try:
            candidates.extend(
                os.path.join(folder, f)
                for f in os.listdir(folder)
                if f.startswith("LotBoundary_") and f.endswith(".txt")
            )
        except OSError:
            continue
        for path in candidates:
            if not os.path.isfile(path):
                continue
            if os.path.abspath(path) == os.path.abspath(last_path()):
                continue
            mtime = os.path.getmtime(path)
            if newest is None or mtime >= newest_mtime:
                newest = path
                newest_mtime = mtime
    return newest
