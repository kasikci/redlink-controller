import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

DEFAULT_CONFIG_PATH = "config.json"


@dataclass
class AppConfig:
    username: str = ""
    password: str = ""
    device_id: int = 0
    control_mode: str = "hysteresis"
    hysteresis_enabled: bool = True
    enable_heat: bool = True
    enable_cool: bool = True
    override_schedule: bool = False
    heat_on_below: float = 68.0
    heat_off_at: float = 71.0
    cool_on_above: float = 76.0
    cool_off_at: float = 74.0
    hold_minutes: int = 60
    poll_interval_seconds: int = 60
    login_refresh_seconds: int = 600
    base_url: str = "https://mytotalconnectcomfort.com"
    time_offset_minutes: Optional[int] = None
    timeout_seconds: int = 20
    bind_host: str = "0.0.0.0"
    bind_port: int = 8000

    def is_configured(self) -> bool:
        return bool(self.username and self.password and self.device_id)

    def to_dict(self, include_password: bool = True) -> Dict[str, Any]:
        data = asdict(self)
        if not include_password:
            data.pop("password", None)
        return data

    def to_public_dict(self) -> Dict[str, Any]:
        data = self.to_dict(include_password=False)
        data["has_password"] = bool(self.password)
        return data


def load_config(path: str) -> AppConfig:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return config_from_dict(data)


def save_config(config: AppConfig, path: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(config.to_dict(include_password=True), handle, indent=2, sort_keys=True)
        handle.write("\n")


def ensure_config(path: str) -> AppConfig:
    try:
        return load_config(path)
    except FileNotFoundError:
        config = AppConfig()
        save_config(config, path)
        return config


def config_from_dict(data: Dict[str, Any]) -> AppConfig:
    hysteresis_enabled = _coerce_bool(data.get("hysteresis_enabled"), default=True)
    control_mode = _coerce_control_mode(data.get("control_mode"))
    if not control_mode:
        control_mode = "hysteresis" if hysteresis_enabled else "schedule"
    return AppConfig(
        username=_coerce_str(data.get("username")),
        password=_coerce_str(data.get("password")),
        device_id=_coerce_int(data.get("device_id"), default=0),
        control_mode=control_mode,
        hysteresis_enabled=hysteresis_enabled,
        enable_heat=_coerce_bool(data.get("enable_heat"), default=True),
        enable_cool=_coerce_bool(data.get("enable_cool"), default=True),
        override_schedule=_coerce_bool(data.get("override_schedule"), default=False),
        heat_on_below=_coerce_float(data.get("heat_on_below"), default=68.0),
        heat_off_at=_coerce_float(data.get("heat_off_at"), default=71.0),
        cool_on_above=_coerce_float(data.get("cool_on_above"), default=76.0),
        cool_off_at=_coerce_float(data.get("cool_off_at"), default=74.0),
        hold_minutes=_coerce_int(data.get("hold_minutes"), default=60),
        poll_interval_seconds=_coerce_int(data.get("poll_interval_seconds"), default=60),
        login_refresh_seconds=_coerce_int(data.get("login_refresh_seconds"), default=600),
        base_url=_coerce_str(data.get("base_url"), default="https://mytotalconnectcomfort.com"),
        time_offset_minutes=_coerce_optional_int(data.get("time_offset_minutes")),
        timeout_seconds=_coerce_int(data.get("timeout_seconds"), default=20),
        bind_host=_coerce_str(data.get("bind_host"), default="0.0.0.0"),
        bind_port=_coerce_int(data.get("bind_port"), default=8000),
    )


def validate_config(config: AppConfig) -> list[str]:
    errors = []
    if config.control_mode not in ("hysteresis", "schedule"):
        errors.append("control_mode must be 'hysteresis' or 'schedule'")
    if config.heat_on_below >= config.heat_off_at:
        errors.append("heat_on_below must be less than heat_off_at")
    if config.cool_on_above <= config.cool_off_at:
        errors.append("cool_on_above must be greater than cool_off_at")
    if config.hold_minutes <= 0:
        errors.append("hold_minutes must be positive")
    if config.poll_interval_seconds <= 0:
        errors.append("poll_interval_seconds must be positive")
    if config.login_refresh_seconds <= 0:
        errors.append("login_refresh_seconds must be positive")
    if config.bind_port <= 0:
        errors.append("bind_port must be positive")
    return errors


def update_config(path: str, updates: Dict[str, Any]) -> AppConfig:
    config = ensure_config(path)
    data = config.to_dict(include_password=True)
    data.update(updates)
    updated = config_from_dict(data)
    save_config(updated, path)
    return updated


def _coerce_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _coerce_int(value: Any, default: int) -> int:
    if value in (None, ""):
        return default
    return int(value)


def _coerce_optional_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    return int(value)


def _coerce_float(value: Any, default: float) -> float:
    if value in (None, ""):
        return float(default)
    return float(value)


def _coerce_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ("true", "1", "yes", "on"):
            return True
        if normalized in ("false", "0", "no", "off"):
            return False
    return bool(value)


def _coerce_control_mode(value: Any) -> str:
    if value is None or value == "":
        return ""
    return str(value).strip().lower()
