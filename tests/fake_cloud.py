"""Stateful fake of the Aqua Temp / HiTemp cloud API.

The fake is written from captured payloads of the real service rather than
from the integration's own parameter files, so that mistakes in those files
are caught instead of mirrored. Two API styles exist:

- ``camel``: https://cloud.linked-go.com:449/crmservice/api (Aqua Temp, HiTemp)
- ``snake``: https://cloud.linked-go.com/cloudservice/api with a ``.json``
  suffix (Aqua Temp apps up to 1.5.8)
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
import copy
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.json import json_dumps
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMockResponse
from yarl import URL

FIXTURES = Path(__file__).parent / "fixtures"

CAMEL_BASE = "https://cloud.linked-go.com:449/crmservice/api/"
SNAKE_BASE = "https://cloud.linked-go.com/cloudservice/api/"

INVALID_TOKEN_MESSAGE = "请重新登录"

KEYS = {
    "camel": {
        "username": "userName",
        "user_id": "userId",
        "object_result": "objectResult",
        "product_ids": "productIds",
        "to_user": "toUser",
        "device_code": "deviceCode",
        "protocal_codes": "protocalCodes",
        "protocol_code": "protocolCode",
        "is_fault": "isFault",
        "device_id": "deviceId",
        "product_id": "productId",
        "nickname": "deviceNickName",
        "model": "custModel",
        "device_status": "deviceStatus",
    },
    "snake": {
        "username": "user_name",
        "user_id": "user_id",
        "object_result": "object_result",
        "product_ids": "product_ids",
        "to_user": "to_user",
        "device_code": "device_code",
        "protocal_codes": "protocal_codes",
        "protocol_code": "protocol_code",
        "is_fault": "is_fault",
        "device_id": "device_id",
        "product_id": "product_id",
        "nickname": "device_nick_name",
        "model": "cust_model",
        "device_status": "device_status",
    },
}

DEVICE_LIST_ENDPOINTS = {
    "app/device/deviceList": "owned",
    "app/device/getMyAppectDeviceShareDataList": "shared",
    "app/device/getMyTobeAppectDeviceShareDataList": "pending",
}


def md5(value: str) -> str:
    """Return the MD5 hex digest the cloud expects for passwords."""
    return hashlib.md5(value.encode()).hexdigest()  # noqa: S324


def load_fixture_json(name: str) -> Any:
    """Load a JSON fixture file."""
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@dataclass
class CloudRequest:
    """A request received by the fake cloud."""

    style: str
    endpoint: str
    url: str
    headers: dict[str, str]
    body: Any
    ssl: Any


@dataclass
class FakeDevice:
    """A heat pump registered in the fake cloud."""

    code: str
    product_id: str
    device_id: str
    nickname: str | None
    model: str | None
    data: dict[str, Any]
    access: dict[str, str] = field(default_factory=dict)
    status: str = "ONLINE"
    is_fault: bool = False
    fault_description: str | None = None

    @classmethod
    def from_fixture(cls, name: str, owner: str) -> FakeDevice:
        """Create a device from a fixture file, owned by ``owner``."""
        raw = load_fixture_json(name)
        return cls(
            code=raw["device_code"],
            product_id=raw["product_id"],
            device_id=raw["device_id"],
            nickname=raw.get("nickname"),
            model=raw.get("model"),
            data=dict(raw["data"]),
            access={owner: "owned"},
        )

    def find_code(self, code: str) -> str | None:
        """Return the stored protocol code matching ``code`` case-insensitively."""
        for existing in self.data:
            if existing.lower() == code.lower():
                return existing
        return None


class FakeCloud:
    """In-memory implementation of the cloud endpoints used by the integration."""

    def __init__(self) -> None:
        """Initialize an empty cloud."""
        self.accounts: dict[str, str] = {}
        self.devices: dict[str, FakeDevice] = {}
        self.requests: list[CloudRequest] = []
        self.tokens: dict[str, str] = {}
        self.network_down = False
        self.single_session = False
        self.data_error: str | None = None
        self.control_error: str | None = None
        self.login_response: dict[str, Any] | None = None
        self.http_status: dict[str, int | list[int]] = {}
        self._token_counter = 0
        self._sessions: list[aiohttp.ClientSession] = []
        self._connectors: list[aiohttp.BaseConnector] = []

    # ------------------------------------------------------------------ setup
    def add_account(self, username: str, password: str) -> None:
        """Register an account."""
        self.accounts[username] = md5(password)

    def add_device(self, device: FakeDevice) -> FakeDevice:
        """Register a device."""
        self.devices[device.code] = device
        return device

    def expire_tokens(self) -> None:
        """Invalidate every issued token, as the cloud does after a new login."""
        self.tokens.clear()

    # ---------------------------------------------------------------- queries
    def endpoint_requests(self, endpoint: str) -> list[CloudRequest]:
        """Return the requests received for an endpoint."""
        return [request for request in self.requests if request.endpoint == endpoint]

    def control_requests(self) -> list[list[dict[str, Any]]]:
        """Return the parameter lists of every device control request."""
        return [
            request.body["param"]
            for request in self.endpoint_requests("app/device/control")
        ]

    def clear_requests(self) -> None:
        """Forget recorded requests."""
        self.requests.clear()

    @property
    def sessions(self) -> list[aiohttp.ClientSession]:
        """Return the sessions created through Home Assistant so far."""
        return list(self._sessions)

    # ------------------------------------------------------------ transport
    @contextmanager
    def patch_sessions(self, hass: HomeAssistant) -> Iterator[None]:
        """Route every Home Assistant aiohttp session to this fake."""

        def create_session(
            hass: HomeAssistant,
            verify_ssl: bool = True,
            auto_cleanup_method: Callable[..., None] | None = None,
            **kwargs: Any,
        ) -> aiohttp.ClientSession:
            connector = aiohttp.BaseConnector()
            session = aiohttp.ClientSession(
                connector=connector, json_serialize=json_dumps
            )
            object.__setattr__(session, "_request", self.request)
            self._connectors.append(connector)
            self._sessions.append(session)
            if auto_cleanup_method is not None:
                auto_cleanup_method(hass, session)
            return session

        with patch(
            "homeassistant.helpers.aiohttp_client._async_create_clientsession",
            side_effect=create_session,
        ):
            yield

    async def async_close(self) -> None:
        """Close every session and connector created by the fake."""
        for session in self._sessions:
            if not session.closed and session.connector is not None:
                await session.close()
        for connector in self._connectors:
            if not connector.closed:
                await connector.close()

    async def request(
        self,
        method: str,
        url: str | URL,
        *,
        headers: dict[str, str] | None = None,
        json: Any = None,
        data: Any = None,
        **kwargs: Any,
    ) -> AiohttpClientMockResponse:
        """Handle a request from an aiohttp session."""
        url = URL(str(url))
        url_str = str(url)

        if url_str.startswith(CAMEL_BASE):
            style = "camel"
            endpoint = url_str.removeprefix(CAMEL_BASE)
        elif url_str.startswith(SNAKE_BASE):
            style = "snake"
            endpoint = url_str.removeprefix(SNAKE_BASE).removesuffix(".json")
        else:
            raise AssertionError(f"Unexpected URL {url_str}")

        body = json if json is not None else data
        self.requests.append(
            CloudRequest(
                style=style,
                endpoint=endpoint,
                url=url_str,
                headers=dict(headers or {}),
                body=copy.deepcopy(body),
                ssl=kwargs.get("ssl", True),
            )
        )

        if method.upper() != "POST":
            raise AssertionError(f"Unexpected method {method}")

        if self.network_down:
            raise aiohttp.ClientConnectionError("Cloud unreachable")

        if (status := self.http_status.get(endpoint)) is not None:
            if isinstance(status, list):
                # One status per request, then back to normal
                status = status.pop(0)
                if not self.http_status[endpoint]:
                    del self.http_status[endpoint]
            return AiohttpClientMockResponse(method, url, status=status)

        result = self._dispatch(style, endpoint, headers or {}, body or {})
        return AiohttpClientMockResponse(method, url, json=result)

    # ------------------------------------------------------------- handlers
    def _response(self, style: str, object_result: Any) -> dict[str, Any]:
        return {
            "error_code": "0",
            "error_msg": "Success",
            "error_msg_code": "",
            KEYS[style]["object_result"]: object_result,
            "isReusltSuc": True,
        }

    def _error(self, style: str, code: str, message: str) -> dict[str, Any]:
        return {
            "error_code": code,
            "error_msg": message,
            "error_msg_code": "",
            KEYS[style]["object_result"]: None,
            "isReusltSuc": False,
        }

    def _user(self, headers: dict[str, str]) -> str | None:
        return self.tokens.get(headers.get("x-token", ""))

    def _dispatch(
        self, style: str, endpoint: str, headers: dict[str, str], body: Any
    ) -> dict[str, Any]:
        keys = KEYS[style]

        if endpoint == "app/user/login":
            if self.login_response is not None:
                return self.login_response

            username = body.get(keys["username"])
            if self.accounts.get(username) != body.get("password"):
                return self._error(style, "-1", "Account or password error")
            if self.single_session:
                self.tokens = {
                    token: user
                    for token, user in self.tokens.items()
                    if user != username
                }
            self._token_counter += 1
            token = f"token-{self._token_counter}"
            self.tokens[token] = username
            return self._response(
                style, {"x-token": token, keys["user_id"]: f"uid-{username}"}
            )

        user = self._user(headers)
        if user is None:
            return self._error(style, "-100", INVALID_TOKEN_MESSAGE)

        if endpoint == "app/user/getUserInfo":
            return self._response(style, {keys["user_id"]: f"uid-{user}"})

        if endpoint in DEVICE_LIST_ENDPOINTS:
            return self._device_list(style, endpoint, user, body)

        if endpoint == "device/sendDevicePassthroughInstruction":
            return self._response(style, None)

        if endpoint == "app/device/control":
            return self._control(style, user, body)

        device = self.devices.get(body.get(keys["device_code"]))
        if device is None or user not in device.access:
            return self._error(style, "-2", "Device not found")

        if endpoint == "app/device/getDataByCode":
            if self.data_error is not None:
                return self._error(style, "-3", self.data_error)
            codes = body.get(keys["protocal_codes"]) or []
            return self._response(
                style,
                [
                    {"code": code, "value": device.data[code]}
                    for code in codes
                    if code in device.data
                ],
            )

        if endpoint == "app/device/getDeviceStatus":
            status = {"status": device.status, keys["is_fault"]: device.is_fault}
            if style == "camel":
                status["is_fault"] = device.is_fault
            return self._response(style, status)

        if endpoint == "app/device/getFaultDataByDeviceCode":
            faults = []
            if device.is_fault and device.fault_description is not None:
                faults.append({"description": device.fault_description})
            return self._response(style, faults)

        raise AssertionError(f"Unexpected endpoint {endpoint}")

    def _device_list(
        self, style: str, endpoint: str, user: str, body: Any
    ) -> dict[str, Any]:
        keys = KEYS[style]
        listing = DEVICE_LIST_ENDPOINTS[endpoint]
        product_ids = body.get(keys["product_ids"]) or []

        if listing != "owned" and body.get(keys["to_user"]) != f"uid-{user}":
            return self._response(style, [])

        items = []
        for device in self.devices.values():
            if device.access.get(user) != listing:
                continue
            if device.product_id not in product_ids:
                continue

            item = {
                keys["device_code"]: device.code,
                keys["device_id"]: device.device_id,
                keys["product_id"]: device.product_id,
                keys["nickname"]: device.nickname,
                keys["model"]: device.model,
                keys["device_status"]: device.status,
                keys["is_fault"]: device.is_fault,
            }
            if style == "camel":
                # The real service returns both spellings for these fields.
                item |= {
                    "device_status": device.status,
                    "is_fault": device.is_fault,
                    "device_id": device.device_id,
                    "device_nick_name": device.nickname,
                }
            items.append(item)

        return self._response(style, items)

    def _control(self, style: str, user: str, body: Any) -> dict[str, Any]:
        keys = KEYS[style]

        if self.control_error is not None:
            return self._error(style, "-4", self.control_error)

        params = body.get("param")
        if not isinstance(params, list) or not params:
            return self._error(style, "-5", "Invalid parameter")

        for param in params:
            device = self.devices.get(param.get(keys["device_code"]))
            code = param.get(keys["protocol_code"])
            if (
                device is None
                or user not in device.access
                or not isinstance(code, str)
                or not code
                or param.get("value") is None
            ):
                return self._error(style, "-5", "Invalid parameter")

        for param in params:
            device = self.devices[param[keys["device_code"]]]
            code = param[keys["protocol_code"]]
            value = param["value"]
            stored_code = device.find_code(code) or code
            device.data[stored_code] = value if isinstance(value, str) else str(value)

        return self._response(style, None)
