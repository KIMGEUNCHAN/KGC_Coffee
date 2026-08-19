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


def daily_directory(now: datetime | None = None) -> str:
    now = now or datetime.now()
    return os.path.join(_log_root, now.strftime(DATE_FORMAT))


def daily_path(now: datetime | None = None) -> str:
    now = now or datetime.now()
    date = now.strftime(DATE_FORMAT)
    return os.path.join(daily_directory(now), f"LotBoundary_{date}.txt")


def ensure_directories(now: datetime | None = None) -> None:
    """Create Log root and today's date folder. No-op if they already exist.

    Call at app start if you want the folders visible before the first lot.
    Write/BeginLot also call this, so you do not have to create folders by hand.
    """
    os.makedirs(_log_root, exist_ok=True)
    os.makedirs(daily_directory(now), exist_ok=True)


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

    _append_and_flush(daily_path(now), line)
    _rewrite_and_flush(last_path(), "".join(_current_lot))


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
