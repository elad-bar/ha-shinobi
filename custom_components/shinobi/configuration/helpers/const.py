"""
Following constants are mandatory for CORE:
    DEFAULT_NAME - Full name for the title of the integration
    DOMAIN - name of component, will be used as component's domain
    SUPPORTED_PLATFORMS - list of supported HA components to initialize
"""

from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PATH,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
)

DEFAULT_NAME = "Shinobi Video"
DOMAIN = "shinobi"

DEFAULT_PORT = 8080

DATA_KEYS = [CONF_HOST, CONF_PATH, CONF_PORT, CONF_SSL, CONF_USERNAME, CONF_PASSWORD]
