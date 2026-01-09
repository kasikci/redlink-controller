from redlink_controller.models import ThermostatStatus
from redlink_controller.service import _is_hold_active


def test_is_hold_active_with_hold_until() -> None:
    status = ThermostatStatus(
        temperature=70.0,
        humidity=40,
        cool_setpoint=76,
        heat_setpoint=68,
        hold_until="11:00 PM",
        status_cool=0,
        status_heat=0,
        fan_mode=0,
        raw={},
    )
    assert _is_hold_active(status) is True


def test_is_hold_active_with_status_flags() -> None:
    status = ThermostatStatus(
        temperature=70.0,
        humidity=40,
        cool_setpoint=76,
        heat_setpoint=68,
        hold_until=None,
        status_cool=1,
        status_heat=0,
        fan_mode=0,
        raw={},
    )
    assert _is_hold_active(status) is True
