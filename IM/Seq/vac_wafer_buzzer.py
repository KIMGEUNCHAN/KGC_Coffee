"""0910 load/unload vacuum-delay wafer check vs buzzer3.

현장 0910 코드가 GitHub 에 없어서, 증상으로 재구성한 모델이다.

증상
  setBuzzer 가 true 가 되는 load/unload seq
  한 호기, 간헐
  load  → buzzer3 ON
  unload → buzzer3 OFF

원인으로 보는 한 줄
  Vac ON/OFF 후 고정 Sleep(nVacDelay) 한 다음
  웨이퍼 센서를 한 번만 읽고
  setBuzzer = not CheckWafer()
  SetBuzzer(3, setBuzzer)
  로 buzzer3 를 묶은 것.

이 모듈은 현장 IO 를 부르지 않는다.
CheckWafer / SetVacuum / SetBuzzer3 는 콜백으로 넣는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def set_buzzer_from_wafer_missing(wafer_present: bool) -> bool:
    """0910 의심 식: setBuzzer = !CheckWafer()."""
    return not wafer_present


def wait_wafer(
    check_wafer,
    expect_present: bool,
    timeout_ms: int,
    poll_ms: int,
    sleep,
) -> bool:
    """고정 Sleep 대신 센서가 기대값과 같아질 때까지 폴링."""
    if poll_ms < 1:
        poll_ms = 10
    elapsed = 0
    while elapsed <= timeout_ms:
        if check_wafer() == expect_present:
            return True
        sleep(poll_ms)
        elapsed += poll_ms
    return check_wafer() == expect_present


def pulse_buzzer3(set_buzzer3, set_buzzer: bool, on_ms: int, sleep) -> None:
    """작업자 알림 펄스. 웨이퍼 센서와 분리한다."""
    if not set_buzzer:
        return
    set_buzzer3(True)
    if on_ms > 0:
        sleep(on_ms)
    set_buzzer3(False)


@dataclass
class LaggingChuck:
    """진공 지령 대비 센서가 settle_ms 만큼 늦은 척.

    한 호기에서 펌프/배관/리크가 느리면 settle 이 delay 보다 커진다.
    """

    settle_ms: int
    t_ms: int = 0
    vacuum_cmd: bool = False
    _change_t: int = 0
    buzzer3: bool = False
    sleeps: list[int] = field(default_factory=list)

    def sleep(self, ms: int) -> None:
        self.sleeps.append(ms)
        self.t_ms += ms

    def set_vacuum(self, on: bool) -> None:
        self.vacuum_cmd = on
        self._change_t = self.t_ms

    def check_wafer(self) -> bool:
        elapsed = self.t_ms - self._change_t
        if elapsed >= self.settle_ms:
            return self.vacuum_cmd
        return not self.vacuum_cmd

    def set_buzzer3(self, on: bool) -> None:
        self.buzzer3 = on


def run_buggy_0910(chuck: LaggingChuck, is_load: bool, vac_delay_ms: int) -> bool:
    """고정 delay + setBuzzer = !CheckWafer() + SetBuzzer(3, setBuzzer).

    load  : Vac ON  → 센서가 아직 OFF 면 setBuzzer true  → buzzer3 ON
    unload: Vac OFF → 센서가 아직 ON  이면 setBuzzer false → buzzer3 OFF
    """
    chuck.set_vacuum(is_load)
    chuck.sleep(vac_delay_ms)
    set_buzzer = set_buzzer_from_wafer_missing(chuck.check_wafer())
    chuck.set_buzzer3(set_buzzer)
    return set_buzzer


def run_fixed(
    chuck: LaggingChuck,
    is_load: bool,
    timeout_ms: int,
    poll_ms: int,
    pulse_ms: int,
    notify: bool,
) -> bool:
    """진공 지령 후 센서 대기. 알림 부저는 센서와 분리."""
    chuck.set_vacuum(is_load)
    ok = wait_wafer(
        chuck.check_wafer,
        is_load,
        timeout_ms,
        poll_ms,
        chuck.sleep,
    )
    if notify:
        pulse_buzzer3(chuck.set_buzzer3, True, pulse_ms, chuck.sleep)
    return ok
