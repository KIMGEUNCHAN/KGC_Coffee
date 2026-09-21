from __future__ import annotations

from IM.Seq.vac_wafer_buzzer import (
    LaggingChuck,
    pulse_buzzer3,
    run_buggy_0910,
    run_fixed,
    set_buzzer_from_wafer_missing,
    wait_wafer,
)

# 0910 쪽 고정 delay. 한 호기는 이보다 진공 settle 이 길다.
VAC_DELAY_MS = 200
FAST_SETTLE_MS = 80
SLOW_SETTLE_MS = 500


def test_set_buzzer_is_inverted_wafer():
    assert set_buzzer_from_wafer_missing(False) is True
    assert set_buzzer_from_wafer_missing(True) is False


def test_slow_unit_load_turns_buzzer3_on():
    chuck = LaggingChuck(settle_ms=SLOW_SETTLE_MS)
    set_buzzer = run_buggy_0910(chuck, is_load=True, vac_delay_ms=VAC_DELAY_MS)
    assert set_buzzer is True
    assert chuck.buzzer3 is True
    assert chuck.check_wafer() is False


def test_slow_unit_unload_turns_buzzer3_off():
    chuck = LaggingChuck(settle_ms=SLOW_SETTLE_MS, vacuum_cmd=True)
    chuck._change_t = -SLOW_SETTLE_MS
    assert chuck.check_wafer() is True

    set_buzzer = run_buggy_0910(chuck, is_load=False, vac_delay_ms=VAC_DELAY_MS)
    assert set_buzzer is False
    assert chuck.buzzer3 is False
    assert chuck.check_wafer() is True


def test_fast_unit_does_not_match_the_complaint():
    load = LaggingChuck(settle_ms=FAST_SETTLE_MS)
    run_buggy_0910(load, is_load=True, vac_delay_ms=VAC_DELAY_MS)
    assert load.buzzer3 is False

    unload = LaggingChuck(settle_ms=FAST_SETTLE_MS, vacuum_cmd=True)
    unload._change_t = -FAST_SETTLE_MS
    run_buggy_0910(unload, is_load=False, vac_delay_ms=VAC_DELAY_MS)
    assert unload.buzzer3 is True


def test_wait_wafer_covers_slow_settle():
    chuck = LaggingChuck(settle_ms=SLOW_SETTLE_MS)
    chuck.set_vacuum(True)
    ok = wait_wafer(chuck.check_wafer, True, timeout_ms=800, poll_ms=50, sleep=chuck.sleep)
    assert ok is True
    assert chuck.t_ms >= SLOW_SETTLE_MS
    assert chuck.check_wafer() is True


def test_wait_wafer_timeout_when_settle_never_comes():
    chuck = LaggingChuck(settle_ms=5000)
    chuck.set_vacuum(True)
    ok = wait_wafer(chuck.check_wafer, True, timeout_ms=100, poll_ms=20, sleep=chuck.sleep)
    assert ok is False
    assert chuck.check_wafer() is False


def test_fixed_load_unload_does_not_bind_buzzer_to_sensor():
    chuck = LaggingChuck(settle_ms=SLOW_SETTLE_MS)
    ok_load = run_fixed(
        chuck, is_load=True, timeout_ms=800, poll_ms=50, pulse_ms=30, notify=True
    )
    assert ok_load is True
    assert chuck.buzzer3 is False

    ok_unload = run_fixed(
        chuck, is_load=False, timeout_ms=800, poll_ms=50, pulse_ms=30, notify=True
    )
    assert ok_unload is True
    assert chuck.buzzer3 is False
    assert chuck.check_wafer() is False


def test_pulse_skips_when_option_off():
    flags = []

    def set_bz(on: bool) -> None:
        flags.append(on)

    pulse_buzzer3(set_bz, False, 10, lambda ms: None)
    assert flags == []
