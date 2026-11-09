from collections.abc import Awaitable, Callable
import logging

from homeassistant.components.climate import HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ..common.api_types import APIParam
from ..common.consts import (
    DATA_ITEM_CONFIG,
    DATA_ITEM_DEVICES,
    DATA_ITEM_LOGIN_DETAILS,
    DEVICE_STATUS,
    DEVICE_STATUS_ONLINE,
    DOMAIN,
    UPDATE_API_INTERVAL,
)
from ..common.utils import convert_range
from .aqua_temp_api import AquaTempAPI
from .aqua_temp_config_manager import AquaTempConfigManager

_LOGGER = logging.getLogger(__name__)


class AquaTempCoordinator(DataUpdateCoordinator):
    """Poll the cloud and hold the state of every device of an account."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        config_manager: AquaTempConfigManager,
    ):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=config_manager.entry_title,
            update_interval=UPDATE_API_INTERVAL,
        )

        self._api = AquaTempAPI(hass, config_manager)
        self._config_manager = config_manager
        self._last_error: str | None = None

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def set_last_error(self, error: str | None):
        self._last_error = error

    @property
    def api_status(self):
        return self._api.is_connected

    @property
    def config_manager(self):
        return self._config_manager

    @property
    def devices(self):
        return self._api.devices

    @property
    def login_details(self):
        return self._api.login_details

    @property
    def device_codes(self) -> list[str]:
        """Return the devices announced to the platforms so far."""
        return self._api.dispatched_devices

    def get_device(self, device_code: str) -> DeviceInfo:
        param_nickname = self._config_manager.get_api_param(APIParam.Nickname)
        param_device_id = self._config_manager.get_api_param(APIParam.DeviceId)
        param_custom_model = self._config_manager.get_api_param(APIParam.CustomModel)

        device_data = self.get_device_data(device_code)
        device_nickname = device_data.get(param_nickname)
        device_model = device_data.get(param_custom_model)
        device_id = device_data.get(param_device_id)

        if param_custom_model in device_data:
            device_model = device_data.get(param_custom_model)

        device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_nickname,
            model=device_model,
        )

        return device_info

    def get_debug_data(self) -> dict:
        config_data = self._config_manager.get_debug_data()

        data = {
            DATA_ITEM_DEVICES: self.devices,
            DATA_ITEM_CONFIG: config_data,
            DATA_ITEM_LOGIN_DETAILS: self._api.login_details,
        }

        return data

    async def _async_update_data(self):
        """Fetch parameters from API endpoint.

        This is the place to pre-process the parameters to lookup tables
        so entities can quickly look up their parameters.
        """
        try:
            await self._api.update()

            config_data = self._config_manager.get_debug_data()

            self._last_error = None

            return {
                DATA_ITEM_DEVICES: self.devices,
                DATA_ITEM_LOGIN_DETAILS: self._api.login_details,
                DATA_ITEM_CONFIG: config_data,
            }

        except Exception as err:
            self._last_error = str(err)
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    def get_temperature_unit(self, device_code: str):
        return self._config_manager.get_temperature_unit(device_code)

    def is_device_online(self, device_code: str) -> bool:
        """Return False only when the cloud reports the device as not online."""
        status = self.get_device_data(device_code).get(DEVICE_STATUS)

        return status is None or str(status).upper() == DEVICE_STATUS_ONLINE

    async def _async_send(
        self, device_code: str, command: Callable[[], Awaitable[None]]
    ) -> None:
        """Send a command to an online device, then refresh its state."""
        if not self.is_device_online(device_code):
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="device_offline",
                translation_placeholders={"device": device_code},
            )

        try:
            await command()

        except HomeAssistantError:
            raise

        except Exception as ex:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"device": device_code, "error": str(ex)},
            ) from ex

        finally:
            await self.async_request_refresh()

    async def set_hvac_mode(self, device_code: str, hvac_mode: HVACMode):
        await self._async_send(
            device_code, lambda: self._api.set_hvac_mode(device_code, hvac_mode)
        )

    async def turn_on(self, device_code: str):
        """Power the device on in the mode it was last running in."""
        await self._async_send(device_code, lambda: self._api.turn_on(device_code))

    async def set_temperature(self, device_code: str, temperature: float):
        await self._async_send(
            device_code, lambda: self._api.set_temperature(device_code, temperature)
        )

    async def set_fan_mode(self, device_code: str, fan_mode):
        await self._async_send(
            device_code, lambda: self._api.set_fan_mode(device_code, fan_mode)
        )

    async def set_protocol_code_value(
        self, device_code: str, protocol_code: str, value
    ):
        await self._async_send(
            device_code,
            lambda: self._api.set_protocol_code_value(
                device_code, protocol_code, value
            ),
        )

    def get_target_temperature_limits(
        self, device_code: str
    ) -> tuple[float | None, float | None, float | None]:
        """Return the minimum, maximum and step of the current target temperature.

        Limits reported by the device for its current mode take precedence.
        Otherwise the range of the writable parameter holding the target is
        used, converted to the unit the device reports in.
        """
        minimum = self._api.get_device_minimum_temperature(device_code)
        maximum = self._api.get_device_maximum_temperature(device_code)
        step = None

        target_code = self._api.get_target_temperature_protocol_code(device_code)
        description = self._config_manager.get_number_description(
            device_code, target_code
        )

        if description is not None:
            static_minimum, static_maximum = convert_range(
                description.native_min_value,
                description.native_max_value,
                description.device_class,
                description.native_unit_of_measurement,
                self.get_temperature_unit(device_code),
            )

            minimum = static_minimum if minimum is None else minimum
            maximum = static_maximum if maximum is None else maximum
            step = description.native_step

        return minimum, maximum, step

    async def set_temperature_unit(self, device_code: str, option: str):
        await self._config_manager.update_temperature_unit(device_code, option)

        await self.async_request_refresh()

    def get_device_data(self, device_code: str) -> dict | None:
        device_data = self._api.get_device_data(device_code)

        return device_data

    def get_device_target_temperature(self, device_code: str) -> float | None:
        target_temperature = self._api.get_device_target_temperature(device_code)

        return target_temperature

    def get_device_current_temperature(self, device_code: str) -> float | None:
        current_temperature = self._api.get_device_current_temperature(device_code)

        return current_temperature

    def get_device_hvac_mode(self, device_code: str) -> HVACMode:
        hvac_mode = self._api.get_device_hvac_mode(device_code)

        return hvac_mode

    def get_device_fan_mode(self, device_code: str) -> str:
        fan_mode = self._api.get_device_fan_mode(device_code)

        return fan_mode

    def get_device_power(self, device_code: str) -> bool:
        power = self._api.get_device_power(device_code)

        return power

    def get_hvac_modes(self, device_code: str) -> list[HVACMode]:
        modes = self._config_manager.get_hvac_modes(device_code)

        result = [HVACMode(mode) for mode in modes]

        return result

    def get_fan_modes(self, device_code: str) -> list[str]:
        modes = self._config_manager.get_fan_modes(device_code)

        return modes
