"""Client for the Aqua Temp / HiTemp cloud API."""

from asyncio import sleep
from copy import copy
import hashlib
import json
import logging
import sys

from aiohttp import ClientError, ClientResponseError, ClientSession
from homeassistant.components.climate.const import HVACMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.redact import async_redact_data
from homeassistant.util import dt as dt_util

from custom_components.aqua_temp.models.exceptions import (
    CloudConnectionError,
    CloudError,
    InvalidCredentialsError,
    InvalidTokenError,
    LoginError,
    OperationFailedException,
)

from ..common.api_types import DEVICE_LISTS, DEVICE_REQUEST_PARAMETERS, APIParam
from ..common.consts import (
    API_MAX_ATTEMPTS,
    APP_HEARTBEAT_CODE,
    APP_HEARTBEAT_VALUE,
    BITWORD_CODES,
    CLOUD_MESSAGES,
    CONFIG_HVAC_MAXIMUM,
    CONFIG_HVAC_MINIMUM,
    CONFIG_HVAC_SET,
    CONFIG_HVAC_TARGET,
    CONFIG_SET_CURRENT_TEMPERATURE,
    CONFIG_SET_FAN,
    CONFIG_SET_MODE,
    CONFIG_SET_POWER,
    CONFIG_SET_TEMPERATURE,
    DEVICE_CONTROL_PARAM,
    DEVICE_CONTROL_VALUE,
    DEVICE_FAULT,
    DEVICE_IS_FAULT,
    DEVICE_STATUS,
    HEADERS,
    HTTP_HEADER_X_TOKEN,
    LIVE_DATA_SETTLE_SECONDS,
    LIVE_PROBE_CODES,
    POWER_MODE_OFF,
    POWER_MODE_ON,
    SIGNAL_AQUA_TEMP_DEVICE_NEW,
    TO_REDACT,
)
from ..common.endpoints import Endpoints
from ..common.utils import normalize_state, safe_float
from .aqua_temp_config_manager import AquaTempConfigManager

_LOGGER = logging.getLogger(__name__)

INVALID_TOKEN_ERROR_CODE = "-100"
INVALID_CREDENTIALS_ERROR_CODE = "-1"
SUCCESS_ERROR_CODE = "0"
SUCCESS_MESSAGE = "Success"


def describe_cloud_message(message) -> str:
    """Add the English meaning to messages the cloud sends in Chinese."""
    meaning = CLOUD_MESSAGES.get(message)

    return str(message) if meaning is None else f"{message} ({meaning})"


def _describe_bitword(value) -> dict:
    """Show a packed switch or output word in the forms needed to decode it."""
    number = safe_float(value)

    if number is None or not number.is_integer() or number < 0:
        return {"value": value}

    number = int(number)

    return {"value": value, "hex": f"0x{number:04X}", "bits": f"{number:016b}"}


class AquaTempAPI:
    _devices: dict
    _login_details: dict | None

    _session: ClientSession | None
    _config_manager: AquaTempConfigManager
    _token: str | None
    _hass: HomeAssistant

    def __init__(
        self,
        hass: HomeAssistant,
        config_manager: AquaTempConfigManager,
        auto_cleanup: bool = True,
    ):
        """Initialize the API client.

        Sessions created with auto_cleanup=False must be released with terminate().
        """

        self._devices = {}
        self._login_details = None

        self._session = None
        self._auto_cleanup = auto_cleanup
        self._token = None
        self._last_request_succeeded = False

        self._hass = hass
        # Each account has its own token, so the headers must not be shared
        self._headers = dict(HEADERS)
        self._config_manager = config_manager

        self._dispatched_devices = []
        self._device_list_request_data = {}

        # Per device: last heartbeat result, probe codes still worth reading,
        # and which requested codes came back with a value
        self._heartbeat_results: dict[str, dict] = {}
        self._probe_codes: dict[str, list[str]] = {}
        self._code_reports: dict[str, dict[str, list[str]]] = {}

    @property
    def is_connected(self):
        """Return whether the API is logged in and its last request succeeded."""
        result = (
            self._session is not None
            and self._token is not None
            and self._last_request_succeeded
        )

        return result

    @property
    def login_details(self):
        result = self._login_details

        return result

    @property
    def devices(self):
        result = self._devices

        return result

    @property
    def dispatched_devices(self) -> list[str]:
        return list(self._dispatched_devices)

    def get_live_data_report(self, device_code: str) -> dict:
        """Return what the last poll learned about the device's codes."""
        report = self._code_reports.get(device_code, {})
        device_data = self._devices.get(device_code, {})

        return {
            "heartbeat": self._heartbeat_results.get(device_code),
            "codes_with_value": report.get("with_value", []),
            "codes_without_value": report.get("without_value", []),
            "bitwords": {
                code: _describe_bitword(device_data[code])
                for code in BITWORD_CODES
                if device_data.get(code) is not None
            },
        }

    def _get_session(self) -> ClientSession:
        if self._session is None:
            self._session = async_create_clientsession(
                hass=self._hass, auto_cleanup=self._auto_cleanup
            )

        return self._session

    async def initialize(self, throw_error: bool = False):
        try:
            _LOGGER.debug(f"Initializing API, Throw Error: {throw_error}")

            if self._session is None:
                self._get_session()

                await self._connect()

        except LoginError as lex:
            if throw_error:
                raise

            _LOGGER.error(f"{lex}, Please update credentials and try again")

        except Exception as ex:
            if throw_error:
                raise

            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.warning(
                f"Failed to initialize session, Error: {ex}, Line: {line_number}"
            )

    async def _connect(self):
        if self._token is None:
            _LOGGER.debug("No token available, Login AquaTemp API and fetching devices")
            await self._login()

            try:
                await self._load_devices()

            except Exception:
                # Without the device list the next attempt has to log in again
                self.set_token()
                raise

    def terminate(self):
        """Release a session created with auto_cleanup=False."""
        if self._session is not None and not self._auto_cleanup:
            self._session.detach()

        self._session = None

    async def update(self):
        """Fetch new state parameters for the sensor."""
        await self._internal_update()

    async def _internal_update(self, attempt: int = 1):
        """Fetch new state parameters for the sensor."""
        error = None
        line_number = None

        try:
            await self._connect()

            for device_code in self._devices:
                await self._update_device(device_code)

        except LoginError as lex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            self.set_token()

            error = lex

        except InvalidTokenError as itex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            self.set_token()

            error = itex

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            error = ex

        if error is not None:
            if attempt < API_MAX_ATTEMPTS:
                await sleep(1)

                await self._internal_update(attempt + 1)

            else:
                _LOGGER.error(
                    f"Failed to update (Attempt #{attempt}), Error: {error}, Line: {line_number}"
                )
                raise error

    async def _update_device(self, device_code: str):
        _LOGGER.debug(f"Starting to update device: {device_code}")

        try:
            new_device = device_code not in self._dispatched_devices

            if new_device:
                device = self.get_device_data(device_code)
                product_id = self._get_device_product_id(device)

                self._config_manager.set_device(device_code, product_id)

            param_keep_alive = self._config_manager.get_api_param(APIParam.KeepAlive)

            if param_keep_alive:
                await self._send_passthrough_instruction(device_code)

            elif self._config_manager.config_data.live_data:
                await self._send_app_heartbeat(device_code)

            else:
                self._set_heartbeat_result(device_code, "disabled")

            await self._fetch_data(device_code)

            if not param_keep_alive:
                await self._fetch_probe_codes(device_code)

            await self._fetch_status(device_code)

            if new_device:
                self._dispatched_devices.append(device_code)

                async_dispatcher_send(
                    self._hass,
                    SIGNAL_AQUA_TEMP_DEVICE_NEW,
                    self._config_manager.entry_id,
                    device_code,
                )

        except ClientResponseError as cre:
            if cre.status == 401:
                raise InvalidTokenError(f"Update device: {device_code}") from cre

            else:
                raise cre

    def set_token(self, token: str | None = None):
        self._device_list_request_data = {}
        self._token = token

        if token is None:
            if HTTP_HEADER_X_TOKEN in self._headers:
                self._headers.pop(HTTP_HEADER_X_TOKEN)
        else:
            self._headers[HTTP_HEADER_X_TOKEN] = token

    async def turn_on(self, device_code: str):
        """Power the device on without changing its mode."""
        await self._set_power_mode(device_code, POWER_MODE_ON)

    async def set_hvac_mode(self, device_code: str, hvac_mode: HVACMode):
        if hvac_mode == HVACMode.OFF:
            await self._set_power_mode(device_code, POWER_MODE_OFF)

        else:
            is_on = self.get_device_power(device_code)

            if not is_on:
                await self._set_power_mode(device_code, POWER_MODE_ON)

                await self._update_device(device_code)

            await self._set_hvac_mode(device_code, hvac_mode)

    async def set_temperature(self, device_code: str, temperature: float):
        """Set the target temperature of the device's current mode."""
        hvac_mode = self.get_device_hvac_mode(device_code)
        target_temperature_pc = self._get_target_temperature_protocol_code(
            device_code, hvac_mode
        )

        set_temp_pc_key = self._config_manager.get_pc_key(
            device_code, CONFIG_SET_TEMPERATURE
        )

        protocol_codes = []
        for protocol_code in (target_temperature_pc, set_temp_pc_key):
            if protocol_code is not None and protocol_code not in protocol_codes:
                protocol_codes.append(protocol_code)

        if not protocol_codes:
            raise OperationFailedException(
                CONFIG_SET_TEMPERATURE,
                temperature,
                "No protocol code is mapped for the target temperature",
            )

        request_data = {
            DEVICE_CONTROL_PARAM: [
                self._control_param(device_code, protocol_code, temperature)
                for protocol_code in protocol_codes
            ]
        }

        await self._perform_action(request_data, protocol_codes[0])

    def _control_param(self, device_code: str, protocol_code: str, value) -> dict:
        param_device_code = self._config_manager.get_api_param(APIParam.DeviceCode)
        param_protocol_code = self._config_manager.get_api_param(APIParam.ProtocolCode)

        return {
            param_device_code: device_code,
            param_protocol_code: protocol_code,
            DEVICE_CONTROL_VALUE: value,
        }

    async def _set_power_mode(self, device_code: str, value):
        """Set new target power mode."""
        power_pc_key = self._config_manager.get_pc_key(device_code, CONFIG_SET_POWER)

        if power_pc_key is None:
            raise OperationFailedException(
                CONFIG_SET_POWER, value, "No protocol code is mapped for power"
            )

        param_device_code = self._config_manager.get_api_param(APIParam.DeviceCode)
        param_protocol_code = self._config_manager.get_api_param(APIParam.ProtocolCode)

        request_data = {
            DEVICE_CONTROL_PARAM: [
                {
                    param_device_code: device_code,
                    param_protocol_code: power_pc_key.lower(),
                    DEVICE_CONTROL_VALUE: value,
                }
            ]
        }

        await self._perform_action(request_data, power_pc_key)

    async def _set_hvac_mode(self, device_code: str, hvac_mode: HVACMode):
        """Switch the mode, keeping the active setpoint on the new mode's target.

        Values the device already reports are not written again.
        """
        if hvac_mode == HVACMode.OFF:
            return

        mode_pc_key = self._config_manager.get_pc_key(device_code, CONFIG_SET_MODE)
        set_temp_pc_key = self._config_manager.get_pc_key(
            device_code, CONFIG_SET_TEMPERATURE
        )
        action_pc_key = self._config_manager.get_hvac_mode_pc_key(
            device_code, hvac_mode, CONFIG_HVAC_SET
        )
        target_temperature_pc = self._get_target_temperature_protocol_code(
            device_code, hvac_mode
        )

        if mode_pc_key is None or action_pc_key is None:
            raise OperationFailedException(
                CONFIG_SET_MODE, hvac_mode, "HVAC mode is not supported by the device"
            )

        device_data = self.get_device_data(device_code)
        target_temperature = (
            None
            if target_temperature_pc is None
            else safe_float(device_data.get(target_temperature_pc))
        )

        _LOGGER.info(
            f"Set HVAC Mode: {hvac_mode}, PC Mode: {action_pc_key}, Target temperature: {target_temperature}"
        )

        control_params = []

        if (
            set_temp_pc_key is not None
            and set_temp_pc_key != target_temperature_pc
            and target_temperature is not None
            and safe_float(device_data.get(set_temp_pc_key)) != target_temperature
        ):
            control_params.append(
                self._control_param(device_code, set_temp_pc_key, target_temperature)
            )

        if str(device_data.get(mode_pc_key)) != str(action_pc_key):
            control_params.append(
                self._control_param(device_code, mode_pc_key, action_pc_key)
            )

        if not control_params:
            _LOGGER.debug(f"Device {device_code} is already in HVAC mode {hvac_mode}")
            return

        request_data = {DEVICE_CONTROL_PARAM: control_params}

        await self._perform_action(request_data, mode_pc_key)

    async def set_fan_mode(self, device_code: str, fan_mode):
        """Set new target fan mode."""
        fan_pc_key = self._config_manager.get_pc_key(device_code, CONFIG_SET_FAN)

        fan_modes = self._config_manager.get_fan_modes(device_code) or {}
        value = fan_modes.get(fan_mode)

        if fan_pc_key is None or value is None:
            raise OperationFailedException(
                CONFIG_SET_FAN, fan_mode, "Fan mode is not supported by the device"
            )

        request_data = {
            DEVICE_CONTROL_PARAM: [self._control_param(device_code, fan_pc_key, value)]
        }

        await self._perform_action(request_data, fan_pc_key)

    async def set_protocol_code_value(
        self, device_code: str, protocol_code: str, value
    ):
        """Set a single protocol code value on the device."""
        param_device_code = self._config_manager.get_api_param(APIParam.DeviceCode)
        param_protocol_code = self._config_manager.get_api_param(APIParam.ProtocolCode)

        request_data = {
            DEVICE_CONTROL_PARAM: [
                {
                    param_device_code: device_code,
                    param_protocol_code: protocol_code,
                    DEVICE_CONTROL_VALUE: value,
                }
            ]
        }

        await self._perform_action(request_data, protocol_code)

    async def _perform_action(
        self, request_data: dict, operation: str, attempt: int = 1
    ):
        error = None

        try:
            param_error_msg = self._config_manager.get_api_param(APIParam.ErrorMessage)
            param_error_code = self._config_manager.get_api_param(APIParam.ErrorCode)

            operation_response = await self._post_request(
                Endpoints.DeviceControl, request_data
            )

            error_msg = operation_response.get(param_error_msg)

            if error_msg != "Success":
                error_code = operation_response.get(param_error_code)
                if error_code == INVALID_TOKEN_ERROR_CODE:
                    _LOGGER.debug(
                        f"Cloud session ended ({describe_cloud_message(error_msg)}), "
                        "logging in again"
                    )

                    self.set_token()

                    error = InvalidTokenError(
                        f"Perform operation {operation}, "
                        f"Data: {json.dumps(request_data)}, "
                        f"Attempt: {attempt}"
                    )

                else:
                    error = OperationFailedException(
                        operation,
                        request_data,
                        f"{error_code}: {describe_cloud_message(error_msg)}",
                    )

        except Exception as ex:
            error = ex

        if error is not None:
            if attempt < API_MAX_ATTEMPTS:
                await sleep(1)

                await self._connect()

                await self._perform_action(request_data, operation, attempt + 1)

            else:
                raise error

    def _check_response(self, response: dict | None, operation: str) -> dict:
        """Return a successful response, raise for cloud errors."""
        param_error_msg = self._config_manager.get_api_param(APIParam.ErrorMessage)
        param_error_code = self._config_manager.get_api_param(APIParam.ErrorCode)

        response = response or {}
        error_msg = response.get(param_error_msg)
        error_code = str(response.get(param_error_code))

        if error_msg == SUCCESS_MESSAGE or error_code == SUCCESS_ERROR_CODE:
            return response

        if error_code == INVALID_TOKEN_ERROR_CODE:
            _LOGGER.debug(
                f"Cloud session ended ({describe_cloud_message(error_msg)}), "
                "logging in again"
            )

            raise InvalidTokenError(operation)

        raise CloudError(
            operation, f"{error_code}: {describe_cloud_message(error_msg)}"
        )

    async def _read_codes(self, device_code: str, codes: list[str]) -> dict:
        """Read protocol codes; codes without a value map to None."""
        param_device_code = self._config_manager.get_api_param(APIParam.DeviceCode)
        param_protocal_codes = self._config_manager.get_api_param(
            APIParam.ProtocalCodes
        )
        param_object_result = self._config_manager.get_api_param(APIParam.ObjectResult)

        data = {
            param_device_code: device_code,
            param_protocal_codes: codes,
        }

        data_response = self._check_response(
            await self._post_request(Endpoints.DeviceData, data),
            f"Fetch data of device {device_code}",
        )

        values = {}
        for object_result_item in data_response.get(param_object_result) or []:
            code = object_result_item.get("code")
            value = object_result_item.get("value")

            if isinstance(value, str) and value == "":
                value = None

            values[code] = value

        return {code: values.get(code) for code in codes}

    async def _fetch_data(self, device_code: str):
        codes = self._config_manager.get_supported_protocol_codes(device_code) or []

        values = await self._read_codes(device_code, codes)

        self._devices[device_code].update(values)
        self._code_reports[device_code] = {
            "with_value": [code for code in codes if values[code] is not None],
            "without_value": [code for code in codes if values[code] is None],
        }

    async def _fetch_probe_codes(self, device_code: str):
        """Read the live codes of the board family the device may support."""
        codes = self._probe_codes.setdefault(device_code, list(LIVE_PROBE_CODES))

        if not codes:
            return

        values = await self._read_probe_batch(device_code, codes)

        # Codes the cloud rejected are not requested again until a restart
        self._probe_codes[device_code] = [code for code in codes if code in values]

        self._devices[device_code].update(values)

        report = self._code_reports.setdefault(
            device_code, {"with_value": [], "without_value": []}
        )
        for code in codes:
            if values.get(code) is None:
                report["without_value"].append(code)
            else:
                report["with_value"].append(code)

    async def _read_probe_batch(self, device_code: str, codes: list[str]) -> dict:
        """Read probe codes, narrowing down codes the cloud rejects."""
        try:
            return await self._read_codes(device_code, codes)

        except CloudError as ex:
            if len(codes) == 1:
                _LOGGER.debug(f"Device {device_code} does not support {codes[0]}: {ex}")
                return {}

        middle = len(codes) // 2

        return {
            **await self._read_probe_batch(device_code, codes[:middle]),
            **await self._read_probe_batch(device_code, codes[middle:]),
        }

    def _set_heartbeat_result(self, device_code: str, result: str):
        self._heartbeat_results[device_code] = {
            "result": result,
            "time": dt_util.utcnow().isoformat(),
        }

    async def _send_app_heartbeat(self, device_code: str):
        """Ask the board to upload its live data, as the official apps do."""
        request_data = {
            DEVICE_CONTROL_PARAM: [
                self._control_param(
                    device_code, APP_HEARTBEAT_CODE, APP_HEARTBEAT_VALUE
                )
            ]
        }

        try:
            self._check_response(
                await self._post_request(
                    Endpoints.DeviceControl, request_data, log_control=False
                ),
                f"Request live data of device {device_code}",
            )

        except CloudError as ex:
            previous = self._heartbeat_results.get(device_code, {})

            if not str(previous.get("result", "")).startswith("rejected"):
                _LOGGER.warning(
                    f"The cloud rejected the live data request of {device_code}, "
                    f"reading the values it already has. Error: {ex}"
                )

            self._set_heartbeat_result(device_code, f"rejected: {ex}")
            return

        self._set_heartbeat_result(device_code, "ok")

        await sleep(LIVE_DATA_SETTLE_SECONDS)

    async def _send_passthrough_instruction(self, device_code: str):
        param_device_code = self._config_manager.get_api_param(APIParam.DeviceCode)

        data = {param_device_code: device_code, "query_instruction": "630300040001CD89"}

        data_response = await self._post_request(
            Endpoints.DevicePassthroughInstruction, data
        )
        error_msg = (data_response or {}).get("error_msg")

        if error_msg != SUCCESS_MESSAGE:
            _LOGGER.error(f"Failed to send passthrough instruction, Error: {error_msg}")

    async def _fetch_status(self, device_code: str):
        """Refresh the online status and fault flag of a device."""
        param_device_code = self._config_manager.get_api_param(APIParam.DeviceCode)
        param_object_result = self._config_manager.get_api_param(APIParam.ObjectResult)
        param_is_fault = self._config_manager.get_api_param(APIParam.IsFault)

        data = {param_device_code: device_code}

        device_status_response = self._check_response(
            await self._post_request(Endpoints.DeviceStatus, data),
            f"Fetch status of device {device_code}",
        )
        object_result = device_status_response.get(param_object_result) or {}

        raw_is_fault = object_result.get(param_is_fault)
        is_fault = (
            None if raw_is_fault is None else normalize_state(raw_is_fault) == "1"
        )
        status = object_result.get("status")

        device_data = self._devices[device_code]
        device_data[DEVICE_IS_FAULT] = is_fault

        if status is not None:
            device_data[DEVICE_STATUS] = status

        fault_description = None

        if is_fault:
            fault_description = await self._fetch_fault_description(device_code)

        if fault_description is None:
            device_data.pop(DEVICE_FAULT, None)
        else:
            device_data[DEVICE_FAULT] = fault_description

    async def _fetch_fault_description(self, device_code: str) -> str | None:
        param_device_code = self._config_manager.get_api_param(APIParam.DeviceCode)
        param_object_result = self._config_manager.get_api_param(APIParam.ObjectResult)

        data = {param_device_code: device_code}

        try:
            device_fault_response = self._check_response(
                await self._post_request(Endpoints.DeviceFault, data),
                f"Fetch fault of device {device_code}",
            )

        except InvalidTokenError:
            raise

        except Exception as ex:
            _LOGGER.warning(f"Failed to fetch the fault description, Error: {ex}")

            return None

        object_results = device_fault_response.get(param_object_result) or []

        if len(object_results) == 0:
            return None

        return object_results[0].get("description")

    async def _login(self):
        """Log in and load the user details.

        Raises InvalidCredentialsError when the cloud rejects the credentials,
        CloudConnectionError when it cannot be reached and LoginError otherwise.
        """
        param_username = self._config_manager.get_api_param(APIParam.Username)
        param_object_result = self._config_manager.get_api_param(APIParam.ObjectResult)
        param_error_code = self._config_manager.get_api_param(APIParam.ErrorCode)

        config_data = self._config_manager.config_data

        plain_password = config_data.password or ""

        password_bytes = bytes(plain_password, "utf-8")

        md5hash = hashlib.new("md5", usedforsecurity=False)
        md5hash.update(password_bytes)

        password_hashed = md5hash.hexdigest()

        data = {param_username: config_data.username, "password": password_hashed}

        self.set_token()

        try:
            login_response = await self._post_request(Endpoints.Login, data) or {}

        except (ClientError, TimeoutError) as ex:
            _LOGGER.error(f"Failed to login, Error: {ex}")

            raise CloudConnectionError(ex) from ex

        if str(login_response.get(param_error_code)) == INVALID_CREDENTIALS_ERROR_CODE:
            _LOGGER.error("Failed to login, the username or password was rejected")

            raise InvalidCredentialsError

        object_result = login_response.get(param_object_result) or {}

        self._login_details = object_result

        token = object_result.get(HTTP_HEADER_X_TOKEN)

        if token is None:
            _LOGGER.error(f"Failed to login, Response: {self._redact(login_response)}")

            raise LoginError

        self.set_token(token)

        try:
            await self._load_user_info()

        except Exception:
            self.set_token()
            raise

    async def _load_user_info(self):
        param_object_result = self._config_manager.get_api_param(APIParam.ObjectResult)
        param_user_id = self._config_manager.get_api_param(APIParam.UserId)

        user_info_response = self._check_response(
            await self._post_request(Endpoints.UserInfo), "Load user info"
        )

        object_result = user_info_response.get(param_object_result) or {}
        user_id = object_result.get(param_user_id)

        for device_list_url in DEVICE_LISTS:
            request_data = {}
            request_data_keys = DEVICE_LISTS[device_list_url]

            for request_data_key in request_data_keys:
                if request_data_key == APIParam.ToUser:
                    value = user_id

                else:
                    value = DEVICE_REQUEST_PARAMETERS.get(request_data_key)

                request_data_param = self._config_manager.get_api_param(
                    request_data_key
                )

                request_data[request_data_param] = value

            self._device_list_request_data[device_list_url] = request_data

    async def _load_devices(self):
        param_object_result = self._config_manager.get_api_param(APIParam.ObjectResult)

        for device_list_url in DEVICE_LISTS:
            request_data = self._device_list_request_data[device_list_url]

            device_code_response = self._check_response(
                await self._post_request(device_list_url, request_data),
                f"List devices ({device_list_url})",
            )

            devices = device_code_response.get(param_object_result) or []

            for device in devices:
                device_code = self._get_device_id(device)

                if device_code is None:
                    _LOGGER.warning(f"Ignoring device without a device code: {device}")
                    continue

                _LOGGER.debug(
                    f"Discover device: {device_code} by {device_list_url}, Data: {device}"
                )

                self._devices[device_code] = device

                _LOGGER.info(f"Discovering device {device_code}")

    async def _post_request(
        self,
        endpoint: Endpoints,
        data: dict | list | None = None,
        log_control: bool = True,
    ) -> dict | None:
        param_url = self._config_manager.get_api_param(APIParam.URL)
        param_suffix = self._config_manager.get_api_param(APIParam.Suffix)

        url = f"{param_url}/{endpoint}{param_suffix}"

        if endpoint == Endpoints.DeviceControl and log_control:
            _LOGGER.info(f"Sending request to control device, Data: {data}")

        try:
            async with self._get_session().post(
                url, headers=self._headers, json=data
            ) as response:
                response.raise_for_status()

                result = await response.json()
                _LOGGER.debug(
                    f"Request to {url}, Body: {self._redact(data)}, "
                    f"Result: {self._redact(result)}"
                )

        except Exception:
            self._last_request_succeeded = False
            raise

        self._last_request_succeeded = True

        return result

    @staticmethod
    def _redact(data):
        """Hide credentials and tokens, which users share when reporting issues."""
        if not isinstance(data, dict | list):
            return data

        return async_redact_data(data, TO_REDACT)

    def get_device_data(self, device_code: str) -> dict:
        device_data = copy(self._devices.get(device_code, {}))

        return device_data

    def get_device_target_temperature(self, device_code: str) -> float | None:
        target_temperature_pc = self.get_target_temperature_protocol_code(device_code)

        device_data = self.get_device_data(device_code)
        target_temperature = device_data.get(target_temperature_pc)

        target_temperature = safe_float(target_temperature)

        return target_temperature

    def get_device_current_temperature(self, device_code: str) -> float | None:
        device_data = self.get_device_data(device_code)
        pc_key = self._config_manager.get_pc_key(
            device_code, CONFIG_SET_CURRENT_TEMPERATURE
        )
        current_temperature = device_data.get(pc_key)

        current_temperature = safe_float(current_temperature)

        return current_temperature

    def get_device_minimum_temperature(self, device_code: str) -> float | None:
        device_data = self.get_device_data(device_code)

        hvac_mode = self.get_device_hvac_mode(device_code)
        key = self._config_manager.get_hvac_mode_pc_key(
            device_code, hvac_mode, CONFIG_HVAC_MINIMUM
        )

        temperature = safe_float(device_data.get(key))

        return temperature

    def get_device_maximum_temperature(self, device_code: str) -> float | None:
        device_data = self.get_device_data(device_code)

        hvac_mode = self.get_device_hvac_mode(device_code)

        key = self._config_manager.get_hvac_mode_pc_key(
            device_code, hvac_mode, CONFIG_HVAC_MAXIMUM
        )

        temperature = safe_float(device_data.get(key))

        return temperature

    def get_device_hvac_mode(self, device_code: str) -> HVACMode:
        device_data = self.get_device_data(device_code)
        pc_key = self._config_manager.get_pc_key(device_code, CONFIG_SET_MODE)
        device_mode = device_data.get(pc_key)

        hvac_mode = self._config_manager.get_hvac_reverse_mapping(
            device_code, device_mode
        )

        try:
            result = HVACMode(hvac_mode)
        except ValueError:
            _LOGGER.warning(
                f"Unknown HVAC mode value '{device_mode}' (mapped to '{hvac_mode}'), defaulting to OFF"
            )
            result = HVACMode.OFF

        return result

    def get_device_fan_mode(self, device_code: str) -> str:
        device_data = self.get_device_data(device_code)
        pc_key = self._config_manager.get_pc_key(device_code, CONFIG_SET_FAN)
        manual_mute = device_data.get(pc_key)

        fan_mode = self._config_manager.get_fan_reverse_mapping(
            device_code, manual_mute
        )

        return fan_mode

    def get_device_power(self, device_code: str) -> bool:
        device_data = self.get_device_data(device_code)
        pc_key = self._config_manager.get_pc_key(device_code, CONFIG_SET_POWER)

        power = device_data.get(pc_key)
        is_on = normalize_state(power) == POWER_MODE_ON

        return is_on

    def get_target_temperature_protocol_code(self, device_code: str) -> str | None:
        """Return the code holding the target of the device's current mode.

        Falls back to the generic setpoint when the mode has no target code,
        for example while the reported mode is unknown.
        """
        hvac_mode = self.get_device_hvac_mode(device_code)
        target_temperature_pc = self._get_target_temperature_protocol_code(
            device_code, hvac_mode
        )

        if target_temperature_pc is None:
            target_temperature_pc = self._config_manager.get_pc_key(
                device_code, CONFIG_SET_TEMPERATURE
            )

        return target_temperature_pc

    def _get_target_temperature_protocol_code(
        self, device_code: str, hvac_mode: HVACMode
    ):
        target_temperature_pc = self._config_manager.get_hvac_mode_pc_key(
            device_code, hvac_mode, CONFIG_HVAC_TARGET
        )

        _LOGGER.debug(f"Target temp PC {target_temperature_pc}, HA Mode: {hvac_mode}")

        return target_temperature_pc

    def _get_device_product_id(self, device_data: dict):
        param = self._config_manager.get_api_param(APIParam.ProductId)
        product_id = device_data.get(param)

        return product_id

    def _get_device_id(self, device_data: dict):
        param = self._config_manager.get_api_param(APIParam.DeviceCode)
        device_code = device_data.get(param)

        return device_code
