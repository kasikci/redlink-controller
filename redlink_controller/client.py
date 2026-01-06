import datetime
import re
import time
from typing import Any, Dict, Optional

import requests

from .endpoints import EndpointConfig
from .exceptions import EndpointNotConfigured, LoginError, RequestError
from .models import ThermostatStatus
from .payloads import (
    build_cancel_hold_payload,
    build_cool_hold_payload,
    build_fan_payload,
    build_heat_hold_payload,
    fan_mode_from_label,
)

_TOKEN_RE = re.compile(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"')


class RedlinkClient:
    def __init__(
        self,
        username: str,
        password: str,
        device_id: int,
        base_url: Optional[str] = None,
        endpoints: Optional[EndpointConfig] = None,
        session: Optional[requests.Session] = None,
        time_offset_minutes: Optional[int] = None,
        timeout: int = 20,
    ) -> None:
        self._username = username
        self._password = password
        self._device_id = str(device_id)
        if endpoints is not None:
            self._endpoints = endpoints
        elif base_url:
            self._endpoints = EndpointConfig(base_url=base_url)
        else:
            self._endpoints = EndpointConfig()
        self._session = session or requests.Session()
        self._timeout = timeout
        self._time_offset_minutes = (
            int(time_offset_minutes)
            if time_offset_minutes is not None
            else _local_time_offset_minutes()
        )
        self._portal_url = self._endpoints.url_for(self._endpoints.login_path)
        self._session.headers.update({"User-Agent": _default_user_agent()})

    @property
    def username(self) -> str:
        return self._username

    @property
    def device_id(self) -> str:
        return self._device_id

    @property
    def base_url(self) -> str:
        return self._endpoints.base_url

    def login(self) -> None:
        response = self._session.get(self._portal_url, timeout=self._timeout)
        if response.status_code != 200:
            raise RequestError(
                "login page returned {0}".format(response.status_code)
            )

        token = _extract_verification_token(response.text)
        payload = {
            "timeOffset": str(self._time_offset_minutes),
            "UserName": self._username,
            "Password": self._password,
            "RememberMe": "false",
        }
        if token:
            payload["__RequestVerificationToken"] = token

        response = self._session.post(
            self._portal_url,
            data=payload,
            timeout=self._timeout,
            allow_redirects=False,
        )
        if response.status_code not in (200, 302, 303):
            raise LoginError(
                "login failed with status {0}".format(response.status_code)
            )

    def get_status(self) -> ThermostatStatus:
        data = self._check_data_session()
        return ThermostatStatus.from_check_data_session(data)

    def set_cool_setpoint(self, setpoint: int, hold_minutes: int = 60) -> None:
        payload = build_cool_hold_payload(
            int(self._device_id),
            setpoint,
            hold_minutes,
        )
        self._submit_control_changes(payload)

    def set_heat_setpoint(self, setpoint: int, hold_minutes: int = 60) -> None:
        payload = build_heat_hold_payload(
            int(self._device_id),
            setpoint,
            hold_minutes,
        )
        self._submit_control_changes(payload)

    def cancel_hold(self) -> None:
        payload = build_cancel_hold_payload(int(self._device_id))
        self._submit_control_changes(payload)

    def set_fan_mode(self, fan_mode: Any) -> None:
        mode_value = (
            fan_mode_from_label(fan_mode)
            if isinstance(fan_mode, str)
            else int(fan_mode)
        )
        payload = build_fan_payload(int(self._device_id), mode_value)
        self._submit_control_changes(payload)

    def get_schedule(self) -> Dict[str, Any]:
        url = self._endpoints.get_schedule_url(self._device_id)
        if not url:
            raise EndpointNotConfigured(
                "get_schedule_path is not configured in EndpointConfig"
            )
        return self._get_json(url)

    def set_schedule(self, payload: Dict[str, Any]) -> None:
        url = self._endpoints.submit_schedule_url()
        if not url:
            raise EndpointNotConfigured(
                "submit_schedule_path is not configured in EndpointConfig"
            )
        self._post_json(url, payload)

    def _check_data_session(self) -> Dict[str, Any]:
        url = self._endpoints.check_data_session_url(self._device_id)
        params = {"_": int(time.time() * 1000)}
        return self._get_json(url, params=params)

    def _submit_control_changes(self, payload: Dict[str, Any]) -> None:
        self._check_data_session()
        url = self._endpoints.submit_control_changes_url()
        self._post_json(url, payload)

    def _get_json(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        response = self._session.get(
            url,
            params=params,
            headers=_ajax_headers(self._portal_url),
            timeout=self._timeout,
        )
        if response.status_code != 200:
            raise RequestError(
                "GET {0} returned {1}".format(url, response.status_code)
            )
        try:
            return response.json()
        except ValueError as exc:
            raise RequestError("response was not JSON") from exc

    def _post_json(self, url: str, payload: Dict[str, Any]) -> None:
        response = self._session.post(
            url,
            json=payload,
            headers=_ajax_headers(self._portal_url),
            timeout=self._timeout,
        )
        if response.status_code != 200:
            raise RequestError(
                "POST {0} returned {1}".format(url, response.status_code)
            )


def _extract_verification_token(html: str) -> Optional[str]:
    match = _TOKEN_RE.search(html)
    if match:
        return match.group(1)
    return None


def _local_time_offset_minutes(now: Optional[datetime.datetime] = None) -> int:
    if now is None:
        now = datetime.datetime.now().astimezone()
    offset = now.utcoffset() or datetime.timedelta(0)
    return int(-offset.total_seconds() / 60)


def _default_user_agent() -> str:
    return (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )


def _ajax_headers(referer: str) -> Dict[str, str]:
    return {
        "Accept": "application/json; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": referer,
    }
