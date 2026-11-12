from datetime import timedelta
from enum import StrEnum

from homeassistant.components.climate.const import FAN_AUTO, FAN_LOW, HVACMode

DOMAIN = "aqua_temp"
DEFAULT_NAME = "Aqua Temp"
SIGNAL_AQUA_TEMP_DEVICE_NEW = f"signal_{DOMAIN}_device_new"
CONFIGURATION_FILE = f"{DOMAIN}.config.json"
STORAGE_VERSION = 1
LEGACY_KEY_FILE = f"{DOMAIN}.key"

UPDATE_API_INTERVAL = timedelta(minutes=5)

ADD_COMPONENT_SIGNALS = [SIGNAL_AQUA_TEMP_DEVICE_NEW]

STORAGE_DATA_KEY = "key"

PROJECT_URL = "https://github.com/goglecm/hitemp"
INVALID_TOKEN_SECTION = f"{PROJECT_URL}#invalid-token"
HITEMP_GUIDE_URL = f"{PROJECT_URL}/blob/Custom-component/docs/HITEMP_PARAMETERS.md"

DEFAULT_ENTRY_ID = "config"

HTTP_HEADER_X_TOKEN = "x-token"

CONF_TITLE = "title"
CONF_API_TYPE = "api_type"
CONF_LIVE_DATA = "live_data"

# Sent by the official apps before reading live values: the board then uploads
# its live block (outputs, switches, fault words, versions) to the cloud.
APP_HEARTBEAT_CODE = "app_heartbeat"
APP_HEARTBEAT_VALUE = "23205"
LIVE_DATA_SETTLE_SECONDS = 2

FAULT_WORD_CODES = [f"Fault{index}" for index in range(1, 11)]
# The PCB software code and version, as on the app's About page
BOARD_VERSION_CODES = ["MainBoard Version", "code_version"]
# Output and switch states packed into one value, bit order unconfirmed
BITWORD_CODES = ["O01~015", "O01~014", "O01~023", "S01~S06", "S01~S10"]
WIFI_VERSION_KEYS = ["wifiSoftwareVer", "wifi_software_ver"]

# Live codes used by the same board family, read separately from the main
# request so that a code the device does not know cannot break the poll.
LIVE_PROBE_CODES = [
    *FAULT_WORD_CODES,
    "ModeState",
    *reversed(BOARD_VERSION_CODES),
    *BITWORD_CODES,
]

# Cloud data types whose values the heat pump reports as whole numbers ("2",
# not "2.0"), so they are written in the same form
INTEGER_CLOUD_TYPES = {"DIGI1", "DIGI2", "DIGI4"}

# Messages the cloud sends in Chinese, with their meaning
CLOUD_MESSAGES = {"请重新登录": "session expired, please log in again"}

PRODUCT_ID_HITEMP = "1245226668902080512"

# Further codes a full scan of an Indol PV300 with the HiTemp product ID found
# (github.com/victor987/hitemp), read for diagnostics until their meaning on
# other models is known
HITEMP_DISCOVERY_CODES = [
    *("2051", "2085", "1129", "1133", "1142", "1151", "T08", "F03", "L28"),
    *("2011", "2012", "2013", "2014", "2026", "2027", "2057", "2058", "2059"),
    *("2068", "2069", "2070", "2071", "T20", "T21"),
    *(f"O{index}" for index in (18, 19, 21, 22, 23, 24, 25, 26, 27, 28)),
    *("M07", "M12", "M13", "M14", "M15", "M16"),
    *("R02", "R11", "R13", "R16", "H09", "H16", "E06"),
    *(f"C0{index}" for index in (1, 2, 3, 5, 6, 7, 8, 9)),
    *("D10", "D11", "D12", "D13"),
    *(f"F{index:02}" for index in (1, 2, 4, 5, 6, 7, 9, 10, 11, 12, 13)),
    *("L02", "L03", "L04", *(f"L{index:02}" for index in range(6, 14))),
    *("L29", "L30", "L31", "L32"),
]
PRODUCT_PROBE_CODES = {PRODUCT_ID_HITEMP: HITEMP_DISCOVERY_CODES}

PRODUCT_IDS = [
    PRODUCT_ID_HITEMP,
    "1132174963097280512",  # Aqua Temp
    "1656269521923575808",  # Aqua Temp
    "1663080854333558784",  # Aqua Temp
    "1596427678569979904",  # Aqua Temp
    "1674238226096406528",  # Aqua Temp
    "1650063968998252544",  # Aqua Temp
    "1668781858447085568",  # Aqua Temp
    "1186904563333062656",  # Aqua Temp
    "1158905952238313472",  # Aqua Temp
    "1442284873216843776",  # Aqua Temp
    "1732565142225256450",  # Aqua Temp
    "1548963836789501952",  # Aqua Temp
    "1669159229372477440",  # Aqua Temp
    "1650758828508766208",  # Aqua Temp
    "1664085465655808000",  # Aqua Temp
]

MANUAL_MUTE_AUTO = "0"
MANUAL_MUTE_LOW = "1"

FAN_MODE_MAPPING = {FAN_AUTO: MANUAL_MUTE_AUTO, FAN_LOW: MANUAL_MUTE_LOW}

POWER_MODE_OFF = "0"
POWER_MODE_ON = "1"

HEADERS = {"Content-Type": "application/json; charset=utf-8"}

API_MAX_ATTEMPTS = 3

DATA_ITEM_DEVICES = "device"
DATA_ITEM_LOGIN_DETAILS = "login-details"
DATA_ITEM_CONFIG = "configuration"

CONFIG_SET_MODE = "mode"
CONFIG_SET_POWER = "power"
CONFIG_SET_TEMPERATURE = "temperature"
CONFIG_SET_FAN = "fan"
CONFIG_SET_CURRENT_TEMPERATURE = "current_temperature"

API_STATUS = "api_status"
CLOUD_STATUS = "cloud_status"

DEVICE_IS_FAULT = "is_fault"
DEVICE_STATUS = "device_status"
DEVICE_FAULT = "fault"
DEVICE_STATUS_ONLINE = "ONLINE"

NO_FAULT = "No fault"
FAULT_WITHOUT_DESCRIPTION = "Fault reported without a description"

PRODUCT_ID_DEFAULT = "default"

CONFIG_HVAC_MODES = "hvac_modes"
CONFIG_HVAC_OFF = str(HVACMode.OFF)
CONFIG_HVAC_HEAT = str(HVACMode.HEAT)
CONFIG_HVAC_COOL = str(HVACMode.COOL)
CONFIG_HVAC_AUTO = str(HVACMode.AUTO)
CONFIG_HVAC_SET = "set"
CONFIG_HVAC_OTHER_VALUES = "other_values"
CONFIG_HVAC_TARGET = "target"
CONFIG_HVAC_MINIMUM = "minimum"
CONFIG_HVAC_MAXIMUM = "maximum"

CONFIG_FAN_MODES = "fan_modes"
CONFIG_FAN_AUTO = "auto"
CONFIG_FAN_LOW = "low"

DEVICE_CONTROL_VALUE = "value"
DEVICE_CONTROL_PARAM = "param"

TO_REDACT = [
    "userId",
    "user_id",
    "toUser",
    "to_user",
    "userName",
    "user_name",
    "username",
    "nickName",
    "nick_name",
    "realName",
    "real_name",
    "userPassword",
    "user_password",
    "password",
    "email",
    "phone",
    "mobile",
    "accessKey",
    "token",
    HTTP_HEADER_X_TOKEN,
]


class ProductParameter(StrEnum):
    MAPPING = "mapping"
    ENTITY_DESCRIPTION = "entity_description"


class CloudStatus(StrEnum):
    """Outcome of the last poll of the cloud."""

    OK = "ok"
    SESSION_EXPIRED = "session_expired"
    LOGIN_REJECTED = "login_rejected"
    CANNOT_CONNECT = "cannot_connect"
    CLOUD_ERROR = "cloud_error"
