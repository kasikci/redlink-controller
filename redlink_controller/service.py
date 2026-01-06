import threading
import time
from dataclasses import asdict
from typing import Any, Dict, Optional

from .client import RedlinkClient
from .config import AppConfig, ensure_config, load_config, validate_config
from .exceptions import LoginError, RequestError
from .hysteresis import ControllerState, HysteresisAction, apply_action, decide_action
from .models import ThermostatStatus


class HysteresisService:
    def __init__(self, config_path: str) -> None:
        self._config_path = config_path
        self._config: Optional[AppConfig] = None
        self._client: Optional[RedlinkClient] = None
        self._client_key: Optional[tuple] = None
        self._state = ControllerState()
        self._last_status: Optional[ThermostatStatus] = None
        self._last_error: Optional[str] = None
        self._last_action_at: Optional[float] = None
        self._last_login_at: Optional[float] = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        ensure_config(self._config_path)
        try:
            self._load_config()
        except Exception as exc:
            self._set_error(str(exc))
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            status = self._last_status
            config = self._config
            state = self._state
            last_error = self._last_error
            last_action_at = self._last_action_at

        status_summary = None
        if status:
            status_summary = {
                "temperature": status.temperature,
                "humidity": status.humidity,
                "cool_setpoint": status.cool_setpoint,
                "heat_setpoint": status.heat_setpoint,
                "hold_until": status.hold_until,
                "status_cool": status.status_cool,
                "status_heat": status.status_heat,
                "fan_mode": status.fan_mode,
            }

        controller_summary = asdict(state)
        controller_summary["last_action_at"] = last_action_at

        return {
            "status": status_summary,
            "controller": controller_summary,
            "config": config.to_public_dict() if config else None,
            "error": last_error,
        }

    def get_config(self) -> Optional[AppConfig]:
        with self._lock:
            return self._config

    def apply_manual_command(self, command: str, payload: Dict[str, Any]) -> None:
        config = self._load_config()
        if not config.is_configured():
            raise ValueError("config missing username/password/device_id")
        self._ensure_client(config)
        if not self._client:
            raise RuntimeError("client not configured")

        self._login_if_needed(config)

        if command == "heat":
            setpoint = int(payload["setpoint"])
            hold_minutes = payload.get("hold_minutes")
            if hold_minutes is None:
                hold_minutes = config.hold_minutes
            hold_minutes = int(hold_minutes)
            self._client.set_heat_setpoint(setpoint, hold_minutes=hold_minutes)
            self._update_state(HysteresisAction(kind="heat", setpoint=setpoint))
            return

        if command == "cool":
            setpoint = int(payload["setpoint"])
            hold_minutes = payload.get("hold_minutes")
            if hold_minutes is None:
                hold_minutes = config.hold_minutes
            hold_minutes = int(hold_minutes)
            self._client.set_cool_setpoint(setpoint, hold_minutes=hold_minutes)
            self._update_state(HysteresisAction(kind="cool", setpoint=setpoint))
            return

        if command == "fan":
            self._client.set_fan_mode(payload["mode"])
            return

        if command == "cancel":
            self._client.cancel_hold()
            self._update_state(HysteresisAction(kind="cancel"))
            return

        raise ValueError("unknown command")

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                config = self._load_config()
                errors = validate_config(config)
                if errors:
                    self._set_error("; ".join(errors))
                    self._sleep(config.poll_interval_seconds)
                    continue

                if not config.is_configured():
                    self._set_error("config missing username/password/device_id")
                    self._sleep(config.poll_interval_seconds)
                    continue

                self._ensure_client(config)
                if not self._client:
                    self._set_error("client not configured")
                    self._sleep(config.poll_interval_seconds)
                    continue

                status = self._fetch_status(config)
                action = decide_action(status.temperature, config, self._state, status.heat_setpoint, status.cool_setpoint)
                if action:
                    self._apply_action(config, action)
                self._update_status(status)
                self._set_error(None)
            except Exception as exc:  # pragma: no cover - safety net
                self._set_error(str(exc))

            self._sleep((self._config or AppConfig()).poll_interval_seconds)

    def _sleep(self, seconds: int) -> None:
        self._stop_event.wait(timeout=max(1, seconds))

    def _load_config(self) -> AppConfig:
        config = load_config(self._config_path)
        with self._lock:
            self._config = config
        return config

    def _ensure_client(self, config: AppConfig) -> None:
        key = (
            config.username,
            config.password,
            config.device_id,
            config.base_url,
            config.time_offset_minutes,
            config.timeout_seconds,
        )
        if self._client_key != key:
            self._client = RedlinkClient(
                username=config.username,
                password=config.password,
                device_id=config.device_id,
                base_url=config.base_url,
                time_offset_minutes=config.time_offset_minutes,
                timeout=config.timeout_seconds,
            )
            self._client_key = key
            self._last_login_at = None

    def _login_if_needed(self, config: AppConfig) -> None:
        if not self._client:
            return
        now = time.time()
        if self._last_login_at is None:
            self._client.login()
            self._last_login_at = now
            return
        if now - self._last_login_at >= config.login_refresh_seconds:
            self._client.login()
            self._last_login_at = now

    def _fetch_status(self, config: AppConfig) -> ThermostatStatus:
        if not self._client:
            raise RuntimeError("client not configured")

        try:
            self._login_if_needed(config)
            return self._client.get_status()
        except RequestError:
            self._client.login()
            self._last_login_at = time.time()
            return self._client.get_status()

    def _apply_action(self, config: AppConfig, action: HysteresisAction) -> None:
        if not self._client:
            raise RuntimeError("client not configured")

        try:
            self._login_if_needed(config)
            if action.kind in ("heat", "heat-idle"):
                setpoint = int(action.setpoint)
                self._client.set_heat_setpoint(setpoint, hold_minutes=config.hold_minutes)
            elif action.kind in ("cool", "cool-idle"):
                setpoint = int(action.setpoint)
                self._client.set_cool_setpoint(setpoint, hold_minutes=config.hold_minutes)
            elif action.kind == "cancel":
                self._client.cancel_hold()
            else:
                raise ValueError("unknown action")
        except (RequestError, LoginError):
            self._client.login()
            self._last_login_at = time.time()
            if action.kind in ("heat", "heat-idle"):
                setpoint = int(action.setpoint)
                self._client.set_heat_setpoint(setpoint, hold_minutes=config.hold_minutes)
            elif action.kind in ("cool", "cool-idle"):
                setpoint = int(action.setpoint)
                self._client.set_cool_setpoint(setpoint, hold_minutes=config.hold_minutes)
            elif action.kind == "cancel":
                self._client.cancel_hold()
        self._update_state(action)

    def _update_state(self, action: HysteresisAction) -> None:
        apply_action(self._state, action)
        self._last_action_at = time.time()

    def _update_status(self, status: ThermostatStatus) -> None:
        with self._lock:
            self._last_status = status

    def _set_error(self, message: Optional[str]) -> None:
        with self._lock:
            self._last_error = message
