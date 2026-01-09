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


def test_heat_idles_when_setpoint_is_higher_than_threshold() -> None:
    config = AppConfig(heat_on_below=68.0, heat_off_at=71.0, cool_on_above=76.0, cool_off_at=74.0)
    state = ControllerState(mode=None)
    action = decide_action(73.0, config, state, heat_setpoint=73.0)
    assert action is not None
    assert action.kind == "heat-idle"
    assert action.setpoint == 68.0


def test_heat_idle_noop_when_already_at_idle_setpoint() -> None:
    config = AppConfig(heat_on_below=68.0, heat_off_at=71.0, cool_on_above=76.0, cool_off_at=74.0)
    state = ControllerState(mode=None)
    action = decide_action(73.0, config, state, heat_setpoint=68.0, cool_setpoint=76.0)
    assert action is None


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
    action = decide_action(74.0, config, state, heat_setpoint=68.0)
    assert action is not None
    assert action.kind == "cool-idle"
    assert action.setpoint == 76.0


def test_cool_idles_without_state_when_setpoint_matches() -> None:
    config = AppConfig(heat_on_below=68.0, heat_off_at=71.0, cool_on_above=76.0, cool_off_at=74.0)
    state = ControllerState(mode=None)
    action = decide_action(74.0, config, state, heat_setpoint=68.0, cool_setpoint=74.0)
    assert action is not None
    assert action.kind == "cool-idle"
    assert action.setpoint == 76.0


def test_cool_idle_noop_when_already_at_idle_setpoint() -> None:
    config = AppConfig(heat_on_below=68.0, heat_off_at=71.0, cool_on_above=76.0, cool_off_at=74.0)
    state = ControllerState(mode=None)
    action = decide_action(72.0, config, state, heat_setpoint=68.0, cool_setpoint=76.0)
    assert action is None


def test_heat_idles_when_mode_stale_and_setpoint_active() -> None:
    config = AppConfig(heat_on_below=68.0, heat_off_at=71.0, cool_on_above=76.0, cool_off_at=74.0)
    state = ControllerState(mode="cool")
    action = decide_action(73.0, config, state, heat_setpoint=71.0, cool_setpoint=73.0)
    assert action is not None
    assert action.kind == "heat-idle"
    assert action.setpoint == 68.0


def test_schedule_mode_disables_hysteresis_actions() -> None:
    config = AppConfig(
        control_mode="schedule",
        hysteresis_enabled=True,
        override_schedule=True,
        heat_on_below=68.0,
        heat_off_at=71.0,
        cool_on_above=76.0,
        cool_off_at=74.0,
    )
    state = ControllerState(mode=None)
    action = decide_action(60.0, config, state, heat_setpoint=65.0)
    assert action is None


def test_schedule_override_reapplies_last_action() -> None:
    config = AppConfig(
        control_mode="hysteresis",
        heat_on_below=68.0,
        heat_off_at=71.0,
        cool_on_above=76.0,
        cool_off_at=74.0,
    )
    state = ControllerState(mode=None, last_action="heat")
    action = decide_action(
        70.0, config, state, heat_setpoint=65.0, cool_setpoint=76.0
    )
    assert action is not None
    assert action.kind == "heat"
    assert action.setpoint == 71.0


def test_schedule_override_establishes_idle_hold_in_deadband() -> None:
    config = AppConfig(
        control_mode="hysteresis",
        heat_on_below=68.0,
        heat_off_at=71.0,
        cool_on_above=76.0,
        cool_off_at=74.0,
    )
    state = ControllerState(mode=None, last_action=None)
    action = decide_action(
        70.0, config, state, heat_setpoint=65.0, cool_setpoint=76.0
    )
    assert action is not None
    assert action.kind == "heat-idle"
    assert action.setpoint == 68.0

