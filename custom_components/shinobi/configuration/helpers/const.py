"""
Following constants are mandatory for CORE:
    DEFAULT_NAME - Full name for the title of the integration
    DOMAIN - name of component, will be used as component's domain
    SUPPORTED_PLATFORMS - list of supported HA components to initialize
"""

from homeassistant.components.binary_sensor import DOMAIN as DOMAIN_BINARY_SENSOR
from homeassistant.components.camera import DOMAIN as DOMAIN_CAMERA
from homeassistant.components.select import DOMAIN as DOMAIN_SELECT
from homeassistant.components.stream import DOMAIN as DOMAIN_STREAM
from homeassistant.components.switch import DOMAIN as DOMAIN_SWITCH
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

DEFAULT_NAME = "Shinobi Video"
DOMAIN = "shinobi"
SUPPORTED_PLATFORMS = [
    DOMAIN_BINARY_SENSOR,
    DOMAIN_CAMERA,
    DOMAIN_SELECT,
    DOMAIN_SWITCH
]


DEFAULT_PORT = 8080

CONFIGURATION_MANAGER = f"cm_{DOMAIN}"


CONF_USE_ORIGINAL_STREAM = "use_original_stream"

DATA_KEYS = [
    CONF_HOST,
    CONF_PATH,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_USE_ORIGINAL_STREAM
]
