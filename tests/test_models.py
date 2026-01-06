from redlink_controller.models import ThermostatStatus


def test_status_parsing_from_check_data_session() -> None:
    data = {
        "latestData": {
            "uiData": {
                "DispTemperature": 71,
                "IndoorHumidity": 45,
                "CoolSetpoint": 75,
                "HeatSetpoint": 68,
                "TemporaryHoldUntilTime": "11:00 PM",
                "StatusCool": 1,
                "StatusHeat": 0,
            },
            "fanData": {"fanMode": 1},
        }
    }
    status = ThermostatStatus.from_check_data_session(data)
    assert status.temperature == 71
    assert status.humidity == 45
    assert status.cool_setpoint == 75
    assert status.heat_setpoint == 68
    assert status.hold_until == "11:00 PM"
    assert status.status_cool == 1
    assert status.status_heat == 0
    assert status.fan_mode == 1
