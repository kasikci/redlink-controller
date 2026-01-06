import datetime
from typing import Dict, Optional

from .models import FanMode, SystemSwitch


def compute_next_period_slot(hold_minutes: int, now: Optional[datetime.datetime] = None) -> int:
    if hold_minutes <= 0:
        raise ValueError("hold_minutes must be positive")
    if now is None:
        now = datetime.datetime.now()
    current_minutes = now.hour * 60 + now.minute
    stop_minutes = (current_minutes + hold_minutes) % (24 * 60)
    return stop_minutes // 15


def build_base_payload(device_id: int) -> Dict[str, Optional[int]]:
    return {
        "CoolNextPeriod": None,
        "CoolSetpoint": None,
        "DeviceID": int(device_id),
        "FanMode": None,
        "HeatNextPeriod": None,
        "HeatSetpoint": None,
        "StatusCool": 0,
        "StatusHeat": 0,
        "SystemSwitch": None,
    }


def build_cool_hold_payload(
    device_id: int,
    setpoint: int,
    hold_minutes: int,
    now: Optional[datetime.datetime] = None,
) -> Dict[str, Optional[int]]:
    payload = build_base_payload(device_id)
    payload.update(
        {
            "CoolSetpoint": int(setpoint),
            "StatusCool": 1,
            "StatusHeat": 1,
            "CoolNextPeriod": compute_next_period_slot(hold_minutes, now=now),
            "SystemSwitch": int(SystemSwitch.COOL),
        }
    )
    return payload


def build_heat_hold_payload(
    device_id: int,
    setpoint: int,
    hold_minutes: int,
    now: Optional[datetime.datetime] = None,
) -> Dict[str, Optional[int]]:
    payload = build_base_payload(device_id)
    payload.update(
        {
            "HeatSetpoint": int(setpoint),
            "StatusCool": 1,
            "StatusHeat": 1,
            "HeatNextPeriod": compute_next_period_slot(hold_minutes, now=now),
            "SystemSwitch": int(SystemSwitch.HEAT),
        }
    )
    return payload


def build_cancel_hold_payload(device_id: int) -> Dict[str, Optional[int]]:
    payload = build_base_payload(device_id)
    payload.update({"StatusCool": 0, "StatusHeat": 0})
    return payload


def build_fan_payload(device_id: int, fan_mode: int) -> Dict[str, Optional[int]]:
    payload = build_base_payload(device_id)
    payload.update({"FanMode": int(fan_mode)})
    return payload


def fan_mode_from_label(label: str) -> int:
    normalized = label.strip().lower()
    if normalized == "auto":
        return int(FanMode.AUTO)
    if normalized == "on":
        return int(FanMode.ON)
    raise ValueError("fan mode must be 'auto' or 'on'")
