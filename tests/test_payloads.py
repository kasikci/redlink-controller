import datetime

from redlink_controller.models import SystemSwitch
from redlink_controller.payloads import (
    build_cancel_hold_payload,
    build_cool_hold_payload,
    build_fan_payload,
    build_heat_hold_payload,
    compute_next_period_slot,
)


def test_compute_next_period_slot_wraps_day() -> None:
    now = datetime.datetime(2023, 1, 1, 23, 30)
    assert compute_next_period_slot(60, now=now) == 2


def test_build_cool_hold_payload_sets_switch_and_period() -> None:
    now = datetime.datetime(2023, 1, 1, 10, 0)
    payload = build_cool_hold_payload(123, 72, 60, now=now)
    assert payload["CoolSetpoint"] == 72
    assert payload["CoolNextPeriod"] == 44
    assert payload["SystemSwitch"] == int(SystemSwitch.COOL)


def test_build_heat_hold_payload_sets_switch_and_period() -> None:
    now = datetime.datetime(2023, 1, 1, 6, 15)
    payload = build_heat_hold_payload(123, 68, 30, now=now)
    assert payload["HeatSetpoint"] == 68
    assert payload["HeatNextPeriod"] == 27
    assert payload["SystemSwitch"] == int(SystemSwitch.HEAT)


def test_build_cancel_hold_payload_clears_status() -> None:
    payload = build_cancel_hold_payload(123)
    assert payload["StatusCool"] == 0
    assert payload["StatusHeat"] == 0


def test_build_fan_payload_sets_mode() -> None:
    payload = build_fan_payload(123, 1)
    assert payload["FanMode"] == 1
