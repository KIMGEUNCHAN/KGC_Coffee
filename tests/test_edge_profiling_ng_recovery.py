from __future__ import annotations

import os
from pathlib import Path

from IM.Logging.edge_profiling_ng_recovery import (
    ALARM_MODULE,
    INSPECT_MODULE,
    PARENT_ALARM,
    OperatorChoice,
    last_path,
    on_edge_profiling_ng,
    on_manual_remove,
    on_manual_remove_confirmed,
    on_operator_choice,
    on_retry,
    on_unload,
    set_log_root,
)


def _last_text(name: str) -> str:
    path = last_path(name)
    return Path(path).read_text(encoding="utf-8")


def test_ng_popup_writes_inspect_and_alarm(tmp_path: Path) -> None:
    set_log_root(tmp_path)
    on_edge_profiling_ng("offset over")

    inspect = _last_text(INSPECT_MODULE)
    alarm = _last_text(ALARM_MODULE)
    assert "EdgeProfiling NG offset over" in inspect
    assert "popup Unload/ManualRemove/Retry" in alarm
    assert PARENT_ALARM not in alarm


def test_unload_raises_parent_inspection_error(tmp_path: Path) -> None:
    set_log_root(tmp_path)
    on_edge_profiling_ng()
    on_unload()

    inspect = _last_text(INSPECT_MODULE)
    alarm = _last_text(ALARM_MODULE)
    assert "Operator=Unload" in inspect
    assert PARENT_ALARM in alarm
    assert os.path.isfile(last_path(INSPECT_MODULE))
    assert os.path.isfile(last_path(ALARM_MODULE))


def test_manual_remove_does_not_raise_inspection_error(tmp_path: Path) -> None:
    set_log_root(tmp_path)
    on_edge_profiling_ng()
    on_manual_remove()
    on_manual_remove_confirmed()

    inspect = _last_text(INSPECT_MODULE)
    alarm = _last_text(ALARM_MODULE)
    assert "Operator=ManualRemove" in inspect
    assert "Operator=ManualRemove Confirmed" in inspect
    assert PARENT_ALARM not in alarm
    assert "Operator=Unload" not in inspect


def test_retry_does_not_raise_inspection_error(tmp_path: Path) -> None:
    set_log_root(tmp_path)
    on_edge_profiling_ng()
    on_retry(2)

    inspect = _last_text(INSPECT_MODULE)
    alarm = _last_text(ALARM_MODULE)
    assert "Operator=Retry Count=2" in inspect
    assert PARENT_ALARM not in alarm


def test_operator_choice_dispatch(tmp_path: Path) -> None:
    set_log_root(tmp_path)
    on_operator_choice(OperatorChoice.UNLOAD)
    assert PARENT_ALARM in _last_text(ALARM_MODULE)

    set_log_root(tmp_path / "manual")
    on_operator_choice(OperatorChoice.MANUAL_REMOVE)
    assert not os.path.isfile(last_path(ALARM_MODULE))
    assert "Operator=ManualRemove" in _last_text(INSPECT_MODULE)

    set_log_root(tmp_path / "retry")
    on_operator_choice(OperatorChoice.RETRY, retry_count=1)
    assert not os.path.isfile(last_path(ALARM_MODULE))
    assert "Operator=Retry Count=1" in _last_text(INSPECT_MODULE)
