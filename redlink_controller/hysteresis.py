from dataclasses import dataclass
from typing import Optional

from .config import AppConfig


@dataclass
class ControllerState:
    mode: Optional[str] = None
    last_action: Optional[str] = None


@dataclass
class HysteresisAction:
    kind: str
    setpoint: Optional[float] = None


def decide_action(
    temperature: Optional[float],
    config: AppConfig,
    state: ControllerState,
    heat_setpoint: Optional[float] = None,
    cool_setpoint: Optional[float] = None,
) -> Optional[HysteresisAction]:
    if temperature is None:
        return None
    if not config.hysteresis_enabled:
        return None

    if state.mode == "heat":
        if not config.enable_heat:
            return HysteresisAction(kind="cancel")
        if temperature >= config.heat_off_at:
            return HysteresisAction(kind="heat-idle", setpoint=config.heat_on_below)
        return None

    if state.mode == "cool":
        if not config.enable_cool:
            return HysteresisAction(kind="cancel")
        if temperature <= config.cool_off_at:
            return HysteresisAction(kind="cool-idle", setpoint=config.cool_on_above)
        return None

    if config.enable_heat and temperature <= config.heat_on_below:
        return HysteresisAction(kind="heat", setpoint=config.heat_off_at)

    if config.enable_cool and temperature >= config.cool_on_above:
        return HysteresisAction(kind="cool", setpoint=config.cool_off_at)

    if config.enable_heat and heat_setpoint == config.heat_off_at:
        if temperature >= config.heat_off_at:
            return HysteresisAction(kind="heat-idle", setpoint=config.heat_on_below)

    if config.enable_cool and cool_setpoint == config.cool_off_at:
        if temperature <= config.cool_off_at:
            return HysteresisAction(kind="cool-idle", setpoint=config.cool_on_above)

    return None


def apply_action(state: ControllerState, action: Optional[HysteresisAction]) -> None:
    if action is None:
        return
    if action.kind == "heat":
        state.mode = "heat"
    elif action.kind == "cool":
        state.mode = "cool"
    elif action.kind in ("heat-idle", "cool-idle", "cancel"):
        state.mode = None
    state.last_action = action.kind
