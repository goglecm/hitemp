"""Tests for the cloud API client."""

from __future__ import annotations

from collections.abc import Callable
import logging
from typing import Any
from unittest.mock import patch

from aiohttp import ClientResponseError
from homeassistant.components.climate import HVACMode
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
import pytest

from custom_components.aqua_temp.common.consts import (
    CONF_API_TYPE,
    HEADERS,
    HTTP_HEADER_X_TOKEN,
)
from custom_components.aqua_temp.managers.aqua_temp_api import AquaTempAPI
from custom_components.aqua_temp.managers.aqua_temp_config_manager import (
    AquaTempConfigManager,
)
from custom_components.aqua_temp.models.exceptions import (
    CloudConnectionError,
    InvalidCredentialsError,
    LoginError,
    OperationFailedException,
)

from .conftest import AQUATEMP_FIXTURE, HITEMP_FIXTURE, PASSWORD, USERNAME
from .fake_cloud import CAMEL_BASE, SNAKE_BASE, FakeCloud, FakeDevice, md5


async def _api(
    hass: HomeAssistant,
    api_type: str = "hi_temp",
    username: str = USERNAME,
    password: str = PASSWORD,
) -> AquaTempAPI:
    manager = AquaTempConfigManager(hass, None)
    await manager.initialize(
        {CONF_USERNAME: username, CONF_PASSWORD: password, CONF_API_TYPE: api_type}
    )
    return AquaTempAPI(hass, manager)


@pytest.mark.parametrize(
    ("api_type", "style", "login_url"),
    [
        ("hi_temp", "camel", f"{CAMEL_BASE}app/user/login"),
        ("aqua_temp", "camel", f"{CAMEL_BASE}app/user/login"),
        ("aqua_temp_old", "snake", f"{SNAKE_BASE}app/user/login.json"),
    ],
)
async def test_login_sends_md5_password(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    api_type: str,
    style: str,
    login_url: str,
) -> None:
    """The password is sent as an MD5 hash to the API type's URL."""
    api = await _api(hass, api_type)

    await api.initialize(True)

    login = fake_cloud.endpoint_requests("app/user/login")[0]
    assert login.url == login_url
    assert login.style == style
    assert PASSWORD not in str(login.body)
    assert md5(PASSWORD) in login.body.values()
    assert api.is_connected


async def test_login_with_wrong_password_raises(
    hass: HomeAssistant, fake_cloud: FakeCloud
) -> None:
    """Rejected credentials raise LoginError when asked to."""
    api = await _api(hass, password="wrong")

    with pytest.raises(LoginError):
        await api.initialize(True)

    assert not api.is_connected


async def test_discovers_owned_and_shared_devices(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
) -> None:
    """Devices are found in the owned, shared and pending lists."""
    owned = add_device(HITEMP_FIXTURE)
    shared = add_device(AQUATEMP_FIXTURE, owner="friend@example.com")
    shared.access[USERNAME] = "shared"

    api = await _api(hass)
    await api.initialize(True)

    assert set(api.devices) == {owned.code, shared.code}
    shared_request = fake_cloud.endpoint_requests(
        "app/device/getMyAppectDeviceShareDataList"
    )[0]
    assert shared_request.body["toUser"] == f"uid-{USERNAME}"


@pytest.mark.parametrize("api_type", ["hi_temp", "aqua_temp_old"])
async def test_update_fetches_product_codes(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    api_type: str,
) -> None:
    """Only the device's product codes are requested, and values are stored."""
    device = add_device(HITEMP_FIXTURE)
    api = await _api(hass, api_type)
    await api.initialize(True)

    await api.update()

    request = fake_cloud.endpoint_requests("app/device/getDataByCode")[0]
    codes_key = "protocalCodes" if api_type == "hi_temp" else "protocal_codes"
    assert "R01" in request.body[codes_key]
    assert "api_status" not in request.body[codes_key]

    data = api.get_device_data(device.code)
    assert data["R01"] == "50.0"
    assert data["T06"] is None


async def test_requests_verify_tls(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
) -> None:
    """Certificate verification stays on for every request."""
    add_device(HITEMP_FIXTURE)
    api = await _api(hass)
    await api.initialize(True)
    await api.update()

    assert fake_cloud.requests
    assert all(request.ssl is True for request in fake_cloud.requests)


async def test_accounts_do_not_share_tokens(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
) -> None:
    """Two accounts keep their own tokens and only see their own devices."""
    fake_cloud.add_account("second@example.com", "other")
    first = add_device(HITEMP_FIXTURE)
    second = add_device(AQUATEMP_FIXTURE, owner="second@example.com")

    api_one = await _api(hass)
    api_two = await _api(hass, username="second@example.com", password="other")
    await api_one.initialize(True)
    await api_two.initialize(True)
    await api_one.update()
    await api_two.update()

    assert set(api_one.devices) == {first.code}
    assert set(api_two.devices) == {second.code}
    assert HTTP_HEADER_X_TOKEN not in HEADERS

    for request in fake_cloud.endpoint_requests("app/device/getDataByCode"):
        owner = fake_cloud.tokens[request.headers[HTTP_HEADER_X_TOKEN]]
        device = fake_cloud.devices[request.body["deviceCode"]]
        assert device.access[owner] == "owned"


async def test_logs_hide_credentials(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Debug logs, which users attach to issues, contain no secrets."""
    caplog.set_level(logging.DEBUG)
    add_device(HITEMP_FIXTURE)
    api = await _api(hass)
    await api.initialize(True)
    await api.update()

    assert "Request to" in caplog.text
    assert md5(PASSWORD) not in caplog.text
    assert PASSWORD not in caplog.text
    for token in fake_cloud.tokens:
        assert token not in caplog.text
    assert f"uid-{USERNAME}" not in caplog.text


@pytest.mark.parametrize(
    ("login_response", "network_down", "error"),
    [
        (None, False, InvalidCredentialsError),
        (None, True, CloudConnectionError),
        ({"error_code": "500", "error_msg": "Busy"}, False, LoginError),
        (
            {"error_code": "0", "error_msg": "Success", "objectResult": None},
            False,
            LoginError,
        ),
    ],
)
async def test_login_failures_are_classified(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    login_response: dict | None,
    network_down: bool,
    error: type[Exception],
) -> None:
    """Rejected credentials are told apart from cloud and network problems."""
    fake_cloud.login_response = login_response
    fake_cloud.network_down = network_down
    api = await _api(hass, password="wrong")

    with pytest.raises(error) as err:
        await api.initialize(True)

    assert type(err.value) is error
    assert not api.is_connected


async def test_failed_discovery_logs_in_again(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
) -> None:
    """If the device list fails after login, the next attempt starts over."""
    device = add_device(HITEMP_FIXTURE)
    fake_cloud.http_status["app/device/deviceList"] = 500
    api = await _api(hass)

    with pytest.raises(ClientResponseError):
        await api.initialize(True)

    assert not api.is_connected

    del fake_cloud.http_status["app/device/deviceList"]
    await api.update()

    assert set(api.devices) == {device.code}
    assert len(fake_cloud.endpoint_requests("app/user/login")) == 2


async def test_http_401_logs_in_again(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
) -> None:
    """An HTTP 401 while reading data renews the token and retries."""
    device = add_device(HITEMP_FIXTURE)
    api = await _api(hass)
    await api.initialize(True)
    fake_cloud.http_status["app/device/getDataByCode"] = [401]

    await api.update()

    assert api.get_device_data(device.code)["R01"] == "50.0"
    assert len(fake_cloud.endpoint_requests("app/user/login")) == 2


async def test_initialize_without_raising_logs_failures(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Background initialisation reports failures in the log instead of raising."""
    api = await _api(hass, password="wrong")
    await api.initialize()
    assert "update credentials" in caplog.text

    fake_cloud.network_down = True
    api = await _api(hass)
    await api.initialize()
    assert "Failed to initialize session" in caplog.text


@pytest.mark.parametrize(
    ("command", "message"),
    [
        (lambda api, code: api.turn_on(code), "power"),
        (lambda api, code: api.set_temperature(code, 40), "target temperature"),
    ],
)
async def test_commands_need_a_mapped_code(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    command: Callable[[AquaTempAPI, str], Any],
    message: str,
) -> None:
    """Commands are refused when the product mapping has no protocol code."""
    device = add_device(HITEMP_FIXTURE)
    api = await _api(hass)
    await api.initialize(True)
    await api.update()

    with (
        patch.object(api._config_manager, "get_pc_key", return_value=None),
        patch.object(api._config_manager, "get_hvac_mode_pc_key", return_value=None),
        pytest.raises(OperationFailedException, match=message),
    ):
        await command(api, device.code)

    assert not fake_cloud.control_requests()


async def test_unsupported_modes_are_refused(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
) -> None:
    """Modes and fan speeds missing from the product mapping are never sent."""
    device = add_device(HITEMP_FIXTURE)
    api = await _api(hass)
    await api.initialize(True)
    await api.update()

    with pytest.raises(OperationFailedException, match="HVAC mode"):
        await api.set_hvac_mode(device.code, HVACMode.COOL)

    with pytest.raises(OperationFailedException, match="Fan mode"):
        await api.set_fan_mode(device.code, "auto")

    assert not fake_cloud.control_requests()


async def test_keep_alive_only_for_old_api(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
) -> None:
    """The old API needs a passthrough instruction before reading data."""
    add_device(HITEMP_FIXTURE)

    for api_type, expected in (("hi_temp", 0), ("aqua_temp_old", 1)):
        fake_cloud.clear_requests()
        api = await _api(hass, api_type)
        await api.initialize(True)
        await api.update()

        passthrough = fake_cloud.endpoint_requests(
            "device/sendDevicePassthroughInstruction"
        )
        assert len(passthrough) == expected
