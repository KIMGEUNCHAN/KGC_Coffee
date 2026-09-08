"""Edge Profiling NG recovery popup log map.

Same clsLog shape as the shop-floor WISVision logger:

    write_log("Inspect", "EdgeProfiling NG Operator=Unload")
    write_log("Alarm", "IM Inspection Error")

Unload raises the parent/host IM Inspection Error.
Manual Remove and Retry write local Inspect lines only.
"""

from __future__ import annotations

import os
import threading
from datetime import datetime
from enum import Enum

DEFAULT_LOG_ROOT = r"C:\WISVision\Log"
DATE_FORMAT = "%Y%m%d"
DATE_FORMATS = ("%Y%m%d", "%Y-%m-%d", "%Y_%m_%d")
INSPECT_MODULE = "Inspect"
ALARM_MODULE = "Alarm"
PARENT_ALARM = "IM Inspection Error"

_lock = threading.Lock()
_log_root = DEFAULT_LOG_ROOT


class OperatorChoice(str, Enum):
    UNLOAD = "Unload"
    MANUAL_REMOVE = "ManualRemove"
    RETRY = "Retry"


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


def daily_path(name: str, now: datetime | None = None) -> str:
    now = now or datetime.now()
    date = date_stamp(now)
    return os.path.join(daily_directory(now), f"{name}_{date}.txt")


def last_path(name: str) -> str:
    return os.path.join(_log_root, f"{name}_LAST.txt")


def write_log(str_name: str, str_log: str | None, b_new_last: bool = False) -> None:
    name = str_name or "System"
    msg = str_log or ""
    now = datetime.now()
    line = f"{now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} : {msg}\n"

    with _lock:
        os.makedirs(_log_root, exist_ok=True)
        os.makedirs(daily_directory(now), exist_ok=True)
        _write_line_flush(last_path(name), line, b_new_last)
        _write_line_flush(daily_path(name, now), line, False)


def on_edge_profiling_ng(reason: str | None = None) -> None:
    msg = "EdgeProfiling NG"
    if reason:
        msg = f"{msg} {reason}"
    write_log(INSPECT_MODULE, msg)
    write_log(ALARM_MODULE, "EdgeProfiling NG popup Unload/ManualRemove/Retry")


def on_operator_choice(choice: OperatorChoice, retry_count: int = 0) -> None:
    if choice is OperatorChoice.UNLOAD:
        on_unload()
    elif choice is OperatorChoice.MANUAL_REMOVE:
        on_manual_remove()
    elif choice is OperatorChoice.RETRY:
        on_retry(retry_count)
    else:
        raise ValueError(choice)


def on_unload() -> None:
    write_log(INSPECT_MODULE, "EdgeProfiling NG Operator=Unload")
    write_log(ALARM_MODULE, PARENT_ALARM)


def on_manual_remove() -> None:
    write_log(INSPECT_MODULE, "EdgeProfiling NG Operator=ManualRemove")


def on_manual_remove_confirmed() -> None:
    write_log(INSPECT_MODULE, "EdgeProfiling NG Operator=ManualRemove Confirmed")


def on_retry(retry_count: int) -> None:
    write_log(INSPECT_MODULE, f"EdgeProfiling NG Operator=Retry Count={retry_count}")


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
