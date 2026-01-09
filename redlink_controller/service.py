import threading
import time
from dataclasses import asdict
from typing import Any, Dict, Optional

import logging

from .client import RedlinkClient
from .config import AppConfig, ensure_config, load_config, validate_config
from .exceptions import LoginError, RequestError
from .hysteresis import ControllerState, HysteresisAction, apply_action, decide_action
from .models import ThermostatStatus

logger = logging.getLogger(__name__)


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
            if self._config:
                logger.info(
                    "Loaded config: control_mode=%s "
                    "enable_heat=%s enable_cool=%s heat_on_below=%s heat_off_at=%s "
                    "cool_on_above=%s cool_off_at=%s hold_minutes=%s poll_interval_seconds=%s",
                    self._config.control_mode,
                    self._config.enable_heat,
                    self._config.enable_cool,
                    self._config.heat_on_below,
                    self._config.heat_off_at,
                    self._config.cool_on_above,
                    self._config.cool_off_at,
                    self._config.hold_minutes,
                    self._config.poll_interval_seconds,
                )
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

        logger.info("Manual command: %s payload=%s", command, _sanitize_payload(payload))
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
                logger.info(
                    "Status: temp=%s heat_setpoint=%s cool_setpoint=%s hold_until=%s "
                    "status_heat=%s status_cool=%s mode=%s control_mode=%s",
                    status.temperature,
                    status.heat_setpoint,
                    status.cool_setpoint,
                    status.hold_until,
                    status.status_heat,
                    status.status_cool,
                    self._state.mode,
                    config.control_mode,
                )
                if config.control_mode == "schedule":
                    if _is_hold_active(status):
                        logger.info("Schedule mode: hold active, cancelling")
                        self._apply_action(config, HysteresisAction(kind="cancel"))
                    self._update_status(status)
                    self._set_error(None)
                    self._sleep(config.poll_interval_seconds)
                    continue
                action = decide_action(status.temperature, config, self._state, status.heat_setpoint, status.cool_setpoint)
                if action:
                    logger.info(
                        "Action: %s setpoint=%s hold_minutes=%s",
                        action.kind,
                        action.setpoint,
                        config.hold_minutes,
                    )
                    self._apply_action(config, action)
                self._update_status(status)
                self._set_error(None)
            except Exception as exc:  # pragma: no cover - safety net
                logger.exception("Service loop error")
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
            logger.info("Logged in to Redlink portal")
            return
        if now - self._last_login_at >= config.login_refresh_seconds:
            self._client.login()
            self._last_login_at = now
            logger.info("Refreshed Redlink session")

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


def _sanitize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    return dict(payload)


def _is_hold_active(status: ThermostatStatus) -> bool:
    if status.hold_until not in (None, "", "--"):
        return True
    if status.status_heat not in (None, 0):
        return True
    if status.status_cool not in (None, 0):
        return True
    return False
