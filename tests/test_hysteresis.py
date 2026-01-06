from redlink_controller.config import AppConfig
from redlink_controller.hysteresis import ControllerState, decide_action


def test_heat_starts_when_below_threshold() -> None:
    config = AppConfig(heat_on_below=68.0, heat_off_at=71.0, cool_on_above=76.0, cool_off_at=74.0)
    state = ControllerState(mode=None)
    action = decide_action(67.5, config, state)
    assert action is not None
    assert action.kind == "heat"
    assert action.setpoint == 71.0


def test_heat_idles_when_at_target() -> None:
    config = AppConfig(heat_on_below=68.0, heat_off_at=71.0, cool_on_above=76.0, cool_off_at=74.0)
    state = ControllerState(mode="heat")
    action = decide_action(71.0, config, state)
    assert action is not None
    assert action.kind == "heat-idle"
    assert action.setpoint == 68.0


def test_heat_idles_without_state_when_setpoint_matches() -> None:
    config = AppConfig(heat_on_below=68.0, heat_off_at=71.0, cool_on_above=76.0, cool_off_at=74.0)
    state = ControllerState(mode=None)
    action = decide_action(71.0, config, state, heat_setpoint=71.0)
    assert action is not None
    assert action.kind == "heat-idle"
    assert action.setpoint == 68.0


def test_cool_starts_when_above_threshold() -> None:
    config = AppConfig(heat_on_below=68.0, heat_off_at=71.0, cool_on_above=76.0, cool_off_at=74.0)
    state = ControllerState(mode=None)
    action = decide_action(77.0, config, state)
    assert action is not None
    assert action.kind == "cool"
    assert action.setpoint == 74.0


def test_cool_idles_when_at_target() -> None:
    config = AppConfig(heat_on_below=68.0, heat_off_at=71.0, cool_on_above=76.0, cool_off_at=74.0)
    state = ControllerState(mode="cool")
    action = decide_action(74.0, config, state)
    assert action is not None
    assert action.kind == "cool-idle"
    assert action.setpoint == 76.0


def test_cool_idles_without_state_when_setpoint_matches() -> None:
    config = AppConfig(heat_on_below=68.0, heat_off_at=71.0, cool_on_above=76.0, cool_off_at=74.0)
    state = ControllerState(mode=None)
    action = decide_action(74.0, config, state, cool_setpoint=74.0)
    assert action is not None
    assert action.kind == "cool-idle"
    assert action.setpoint == 76.0


def test_hysteresis_disabled_no_action() -> None:
    config = AppConfig(hysteresis_enabled=False)
    state = ControllerState(mode=None)
    action = decide_action(60.0, config, state)
    assert action is None
