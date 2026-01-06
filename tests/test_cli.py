import argparse

import pytest

from redlink_controller import cli
from redlink_controller.config import AppConfig


def test_parse_args_cool_defaults_hold_minutes() -> None:
    args = cli.parse_args(["cool", "--setpoint", "72"])
    assert args.command == "cool"
    assert args.hold_minutes == cli.DEFAULT_HOLD_MINUTES


def test_parse_args_server() -> None:
    args = cli.parse_args(["server", "--host", "0.0.0.0", "--port", "9000"])
    assert args.command == "server"
    assert args.host == "0.0.0.0"
    assert args.port == 9000


def test_resolve_credentials_prefers_args() -> None:
    args = argparse.Namespace(username="u", password="p", device_id=123)
    config = AppConfig(username="config-u", password="config-p", device_id=999)
    env = {
        "REDLINK_USERNAME": "env-u",
        "REDLINK_PASSWORD": "env-p",
        "REDLINK_DEVICE_ID": "999",
    }
    username, password, device_id = cli.resolve_credentials(
        args, environ=env, config=config, password_prompt=None
    )
    assert username == "u"
    assert password == "p"
    assert device_id == 123


def test_resolve_credentials_env_fallback() -> None:
    args = argparse.Namespace(username=None, password=None, device_id=None)
    env = {
        "REDLINK_USERNAME": "env-u",
        "REDLINK_PASSWORD": "env-p",
        "REDLINK_DEVICE_ID": "456",
    }
    username, password, device_id = cli.resolve_credentials(
        args, environ=env, config=None, password_prompt=None
    )
    assert username == "env-u"
    assert password == "env-p"
    assert device_id == 456


def test_resolve_credentials_config_fallback() -> None:
    args = argparse.Namespace(username=None, password=None, device_id=None)
    config = AppConfig(username="config-u", password="config-p", device_id=321)
    username, password, device_id = cli.resolve_credentials(
        args, environ={}, config=config, password_prompt=None
    )
    assert username == "config-u"
    assert password == "config-p"
    assert device_id == 321


def test_resolve_credentials_missing_raises() -> None:
    args = argparse.Namespace(username=None, password=None, device_id=None)
    with pytest.raises(ValueError):
        cli.resolve_credentials(args, environ={}, config=None, password_prompt=None)


def test_resolve_credentials_invalid_device_id_raises() -> None:
    args = argparse.Namespace(username=None, password=None, device_id=None)
    env = {
        "REDLINK_USERNAME": "env-u",
        "REDLINK_PASSWORD": "env-p",
        "REDLINK_DEVICE_ID": "abc",
    }
    with pytest.raises(ValueError):
        cli.resolve_credentials(args, environ=env, config=None, password_prompt=None)


def test_resolve_endpoints_from_env() -> None:
    args = argparse.Namespace(
        base_url=None,
        schedule_get_path=None,
        schedule_submit_path=None,
    )
    env = {
        "REDLINK_BASE_URL": "https://example.com",
        "REDLINK_SCHEDULE_GET_PATH": "/path/{device_id}",
        "REDLINK_SCHEDULE_SUBMIT_PATH": "/submit",
    }
    endpoints = cli.resolve_endpoints(args, environ=env, config=None)
    assert endpoints.base_url == "https://example.com"
    assert endpoints.get_schedule_path == "/path/{device_id}"
    assert endpoints.submit_schedule_path == "/submit"
