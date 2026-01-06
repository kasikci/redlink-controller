import argparse
import getpass
import json
import os
import sys
from typing import Any, Dict, List, Optional

from .client import RedlinkClient
from .config import DEFAULT_CONFIG_PATH, AppConfig, load_config
from .endpoints import EndpointConfig
from .exceptions import EndpointNotConfigured, LoginError, RequestError
from .models import ThermostatStatus

DEFAULT_HOLD_MINUTES = 60


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Control Honeywell Total Connect Comfort / Redlink thermostats."
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG_PATH,
        help="Path to config file (default: config.json)",
    )
    parser.add_argument("--username", help="Account username (or REDLINK_USERNAME)")
    parser.add_argument("--password", help="Account password (or REDLINK_PASSWORD)")
    parser.add_argument(
        "--device-id",
        type=int,
        help="Device ID from the portal URL (or REDLINK_DEVICE_ID)",
    )
    parser.add_argument(
        "--base-url",
        help="Override base URL (or REDLINK_BASE_URL)",
    )
    parser.add_argument(
        "--schedule-get-path",
        help="Schedule GET path (or REDLINK_SCHEDULE_GET_PATH)",
    )
    parser.add_argument(
        "--schedule-submit-path",
        help="Schedule submit path (or REDLINK_SCHEDULE_SUBMIT_PATH)",
    )
    parser.add_argument(
        "--time-offset-minutes",
        type=int,
        help="Override time offset minutes (or REDLINK_TIME_OFFSET_MINUTES)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        help="Request timeout seconds (or REDLINK_TIMEOUT)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Print current thermostat status")

    cool_parser = subparsers.add_parser("cool", help="Set a temporary cool hold")
    cool_parser.add_argument("--setpoint", type=int, required=True)
    cool_parser.add_argument(
        "--hold-minutes", type=int, default=DEFAULT_HOLD_MINUTES
    )

    heat_parser = subparsers.add_parser("heat", help="Set a temporary heat hold")
    heat_parser.add_argument("--setpoint", type=int, required=True)
    heat_parser.add_argument(
        "--hold-minutes", type=int, default=DEFAULT_HOLD_MINUTES
    )

    fan_parser = subparsers.add_parser("fan", help="Set the fan mode")
    fan_parser.add_argument(
        "--mode",
        required=True,
        help="Fan mode (auto, on, 0, 1)",
    )

    subparsers.add_parser("cancel", help="Cancel the current hold")

    schedule_get = subparsers.add_parser("schedule-get", help="Fetch schedule JSON")
    schedule_get.add_argument("--out", dest="out_path", help="Write to file")

    schedule_set = subparsers.add_parser("schedule-set", help="Submit schedule JSON")
    schedule_set.add_argument("--in", dest="in_path", required=True)

    server_parser = subparsers.add_parser(
        "server", help="Start the local web controller"
    )
    server_parser.add_argument("--host", help="Bind host (default from config)")
    server_parser.add_argument("--port", type=int, help="Bind port (default from config)")

    return parser


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = build_parser()
    return parser.parse_args(argv)


def resolve_credentials(
    args: argparse.Namespace,
    environ: Optional[Dict[str, str]] = None,
    config: Optional[AppConfig] = None,
    password_prompt: Optional[Any] = None,
) -> tuple[str, str, int]:
    env = os.environ if environ is None else environ
    username = args.username or env.get("REDLINK_USERNAME") or _get_config_value(config, "username")
    password = args.password or env.get("REDLINK_PASSWORD") or _get_config_value(config, "password")
    device_id = args.device_id or _get_env_int(env, "REDLINK_DEVICE_ID") or _get_config_value(config, "device_id")

    if not password and password_prompt is not None:
        password = password_prompt("Password: ")

    if not username or not password or not device_id:
        raise ValueError("username, password, and device id are required")

    return username, password, device_id


def resolve_endpoints(
    args: argparse.Namespace, environ: Optional[Dict[str, str]] = None, config: Optional[AppConfig] = None
) -> EndpointConfig:
    env = os.environ if environ is None else environ
    base_url = args.base_url or env.get("REDLINK_BASE_URL") or _get_config_value(config, "base_url")
    schedule_get = args.schedule_get_path or env.get("REDLINK_SCHEDULE_GET_PATH")
    schedule_submit = (
        args.schedule_submit_path or env.get("REDLINK_SCHEDULE_SUBMIT_PATH")
    )
    kwargs: Dict[str, Any] = {}
    if base_url:
        kwargs["base_url"] = base_url
    if schedule_get:
        kwargs["get_schedule_path"] = schedule_get
    if schedule_submit:
        kwargs["submit_schedule_path"] = schedule_submit
    return EndpointConfig(**kwargs)


def resolve_time_offset(
    args: argparse.Namespace, environ: Optional[Dict[str, str]] = None, config: Optional[AppConfig] = None
) -> Optional[int]:
    env = os.environ if environ is None else environ
    if args.time_offset_minutes is not None:
        return args.time_offset_minutes
    return _get_env_int(env, "REDLINK_TIME_OFFSET_MINUTES") or _get_config_value(config, "time_offset_minutes")


def resolve_timeout(
    args: argparse.Namespace, environ: Optional[Dict[str, str]] = None, config: Optional[AppConfig] = None
) -> Optional[int]:
    env = os.environ if environ is None else environ
    if args.timeout is not None:
        return args.timeout
    return _get_env_int(env, "REDLINK_TIMEOUT") or _get_config_value(config, "timeout_seconds")


def build_client(
    args: argparse.Namespace,
    environ: Optional[Dict[str, str]] = None,
    password_prompt: Optional[Any] = None,
) -> RedlinkClient:
    config = _load_config_file(args.config)
    username, password, device_id = resolve_credentials(
        args,
        environ=environ,
        config=config,
        password_prompt=password_prompt,
    )
    endpoints = resolve_endpoints(args, environ=environ, config=config)
    time_offset = resolve_time_offset(args, environ=environ, config=config)
    timeout = resolve_timeout(args, environ=environ, config=config)

    return RedlinkClient(
        username=username,
        password=password,
        device_id=device_id,
        endpoints=endpoints,
        time_offset_minutes=time_offset,
        timeout=timeout if timeout is not None else 20,
    )


def run_command(args: argparse.Namespace) -> None:
    if args.command == "server":
        from .server import run_server

        run_server(config_path=args.config, host=args.host, port=args.port)
        return

    client = build_client(args, password_prompt=getpass.getpass)
    client.login()

    if args.command == "status":
        status = client.get_status()
        _print_status(status)
        return

    if args.command == "cool":
        client.set_cool_setpoint(args.setpoint, hold_minutes=args.hold_minutes)
        print("OK")
        return

    if args.command == "heat":
        client.set_heat_setpoint(args.setpoint, hold_minutes=args.hold_minutes)
        print("OK")
        return

    if args.command == "fan":
        client.set_fan_mode(_parse_fan_mode(args.mode))
        print("OK")
        return

    if args.command == "cancel":
        client.cancel_hold()
        print("OK")
        return

    if args.command == "schedule-get":
        schedule = client.get_schedule()
        _write_json(schedule, args.out_path)
        return

    if args.command == "schedule-set":
        payload = _load_json(args.in_path)
        client.set_schedule(payload)
        print("OK")
        return

    raise ValueError("unknown command")


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    try:
        run_command(args)
    except (ValueError, LoginError, RequestError, EndpointNotConfigured) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(payload: Dict[str, Any], path: Optional[str]) -> None:
    if path:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
    else:
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")


def _print_status(status: ThermostatStatus) -> None:
    summary = {
        "temperature": status.temperature,
        "humidity": status.humidity,
        "cool_setpoint": status.cool_setpoint,
        "heat_setpoint": status.heat_setpoint,
        "hold_until": status.hold_until,
        "status_cool": status.status_cool,
        "status_heat": status.status_heat,
        "fan_mode": status.fan_mode,
    }
    json.dump(summary, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


def _parse_fan_mode(value: str) -> Any:
    try:
        return int(value)
    except ValueError:
        return value


def _load_config_file(path: Optional[str]) -> Optional[AppConfig]:
    if not path:
        return None
    try:
        return load_config(path)
    except FileNotFoundError:
        return None


def _get_config_value(config: Optional[AppConfig], key: str) -> Any:
    if not config:
        return None
    return getattr(config, key, None)


def _get_env_int(env: Dict[str, str], key: str) -> Optional[int]:
    value = env.get(key)
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError("{0} must be an integer".format(key)) from exc
