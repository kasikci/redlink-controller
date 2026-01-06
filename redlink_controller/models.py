from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Dict, Optional


class SystemSwitch(IntEnum):
    OFF = 0
    HEAT = 1
    AUTO = 2
    COOL = 3


class FanMode(IntEnum):
    AUTO = 0
    ON = 1


@dataclass
class ThermostatStatus:
    temperature: Optional[float]
    humidity: Optional[int]
    cool_setpoint: Optional[int]
    heat_setpoint: Optional[int]
    hold_until: Optional[str]
    status_cool: Optional[int]
    status_heat: Optional[int]
    fan_mode: Optional[int]
    raw: Dict[str, Any]

    @classmethod
    def from_check_data_session(cls, data: Dict[str, Any]) -> "ThermostatStatus":
        latest = data.get("latestData", {})
        ui_data = latest.get("uiData", {})
        fan_data = latest.get("fanData", {})
        return cls(
            temperature=ui_data.get("DispTemperature"),
            humidity=ui_data.get("IndoorHumidity"),
            cool_setpoint=ui_data.get("CoolSetpoint"),
            heat_setpoint=ui_data.get("HeatSetpoint"),
            hold_until=ui_data.get("TemporaryHoldUntilTime"),
            status_cool=ui_data.get("StatusCool"),
            status_heat=ui_data.get("StatusHeat"),
            fan_mode=fan_data.get("fanMode"),
            raw=data,
        )
