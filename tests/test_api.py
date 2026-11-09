"""Tests for the cloud API client."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
import pytest

from custom_components.aqua_temp.common.consts import CONF_API_TYPE
from custom_components.aqua_temp.managers.aqua_temp_api import AquaTempAPI
from custom_components.aqua_temp.managers.aqua_temp_config_manager import (
    AquaTempConfigManager,
)
from custom_components.aqua_temp.models.exceptions import LoginError

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
