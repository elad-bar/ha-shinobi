from homeassistant.components.binary_sensor import (
    DOMAIN as DOMAIN_BINARY_SENSOR,
    BinarySensorDeviceClass,
)
from homeassistant.components.camera import DOMAIN as DOMAIN_CAMERA
from homeassistant.components.select import DOMAIN as DOMAIN_SELECT
from homeassistant.components.stream import DOMAIN as DOMAIN_STREAM
from homeassistant.components.switch import DOMAIN as DOMAIN_SWITCH

DOMAIN = "shinobi"
DEFAULT_NAME = "Shinobi Video"
DEFAULT_PORT = 8080

SUPPORTED_PLATFORMS = [
    DOMAIN_BINARY_SENSOR,
    DOMAIN_CAMERA,
    DOMAIN_SELECT,
    DOMAIN_SWITCH
]

PLATFORMS = {domain: f"{DOMAIN}_{domain}_UPDATE_SIGNAL" for domain in SUPPORTED_PLATFORMS}
