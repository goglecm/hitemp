from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import selector
import probatio as vol
from probatio import Schema

from ..common.api_types import API_TYPE_LEGACY, API_TYPES, APIType
from ..common.consts import CONF_API_TYPE, CONF_TITLE, DEFAULT_NAME

PASSWORD_SELECTOR = selector.TextSelector(
    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
)


class ConfigData:
    _username: str | None
    _password: str | None
    _api_type: str | None

    def __init__(self):
        self._username = None
        self._password = None
        self._api_type = None

    @property
    def username(self) -> str:
        username = self._username

        return username

    @property
    def password(self) -> str:
        password = self._password

        return password

    @property
    def api_type(self) -> str:
        api_type = self._api_type

        return api_type

    def update(self, data: dict):
        self._password = data.get(CONF_PASSWORD)
        self._username = data.get(CONF_USERNAME)

        api_type = data.get(CONF_API_TYPE, str(APIType.AquaTempOld))

        if api_type in API_TYPE_LEGACY:
            api_type = str(API_TYPE_LEGACY.get(api_type))

        self._api_type = api_type

    @staticmethod
    def from_dict(data: dict) -> ConfigData:
        config_data = ConfigData()
        config_data.update(data)

        return config_data

    @property
    def unique_id(self) -> str:
        """Identify the account, which may only be configured once."""
        return f"{self.api_type}_{(self.username or '').strip().lower()}"

    def to_dict(self):
        obj = {
            CONF_USERNAME: self.username,
        }

        return obj

    def __repr__(self):
        to_string = f"{self.to_dict()}"

        return to_string

    @staticmethod
    def default_schema(
        user_input: dict | None, password_required: bool = True
    ) -> Schema:
        """Return the account form; passwords are never pre-filled."""
        if user_input is None:
            user_input = {}

        password_key = (
            vol.Required(CONF_PASSWORD)
            if password_required
            else vol.Optional(CONF_PASSWORD)
        )

        new_user_input = {
            vol.Required(
                CONF_TITLE, default=user_input.get(CONF_TITLE, DEFAULT_NAME)
            ): str,
            _required(CONF_USERNAME, user_input.get(CONF_USERNAME)): str,
            password_key: PASSWORD_SELECTOR,
            _required(CONF_API_TYPE, user_input.get(CONF_API_TYPE)): (
                selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=API_TYPES,
                        translation_key=CONF_API_TYPE,
                    )
                )
            ),
        }

        schema = vol.Schema(new_user_input)

        return schema

    @staticmethod
    def password_schema() -> Schema:
        """Return the form asking only for a new password."""
        return vol.Schema({vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR})


def _required(key: str, default: str | None) -> vol.Required:
    if default is None or default == "":
        return vol.Required(key)

    return vol.Required(key, default=default)
