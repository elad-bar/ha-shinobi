from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PATH,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
    STATE_OFF,
    STATE_ON,
)

from .component_overrides.const import *

ENTITY_ID = "id"
ENTITY_NAME = "name"
ENTITY_STATE = "state"
ENTITY_ATTRIBUTES = "attributes"
ENTITY_ICON = "icon"
ENTITY_UNIQUE_ID = "unique-id"
ENTITY_BINARY_SENSOR_DEVICE_CLASS = "binary-sensor-device-class"
ENTITY_DEVICE_NAME = "device-name"
ENTITY_MONITOR_DETAILS = "monitor-details"
ENTITY_DISABLED = "disabled"
ENTITY_DOMAIN = "domain"
ENTITY_STATUS = "status"
ENTITY_CONFIG_ENTRY_ID = "entry_id"

CONFIG_FLOW_DATA = "config_flow_data"
CONFIG_FLOW_OPTIONS = "config_flow_options"
CONFIG_FLOW_INIT = "config_flow_init"

CONF_USE_ORIGINAL_STREAM = "use_original_stream"

CONF_ARR = [CONF_USERNAME, CONF_PASSWORD, CONF_HOST, CONF_PORT, CONF_SSL, CONF_PATH, CONF_USE_ORIGINAL_STREAM]

STORAGE_VERSION = 1

DEFAULT_PORT = 8080

PASSWORD_MANAGER = f"pm_{DOMAIN}"
DATA = f"data_{DOMAIN}"

DOMAIN_KEY_FILE = f"{DOMAIN}.key"
