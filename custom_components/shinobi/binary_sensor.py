"""
Support for Shinobi Video binary sensors.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/binary_sensor.shinobi/
"""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant

from .component.helpers.const import *
from .component.models.shinobi_entity import ShinobiEntity
from .core.models.base_entity import async_setup_base_entry
from .core.models.entity_data import EntityData

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = [DOMAIN]

CURRENT_DOMAIN = DOMAIN_BINARY_SENSOR


def get_binary_sensor(hass: HomeAssistant, entity: EntityData):
    binary_sensor = BaseBinarySensor()
    binary_sensor.initialize(hass, entity, CURRENT_DOMAIN)

    return binary_sensor


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up the Shinobi Video Binary Sensor."""
    await async_setup_base_entry(
        hass, config_entry, async_add_devices, CURRENT_DOMAIN, get_binary_sensor
    )


async def async_unload_entry(hass, config_entry):
    _LOGGER.info(f"Unload entry for {CURRENT_DOMAIN} domain: {config_entry}")

    return True


class BaseBinarySensor(BinarySensorEntity, ShinobiEntity):
    """Representation a binary sensor that is updated."""

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self.entity.state == STATE_ON

    @property
    def device_class(self) -> BinarySensorDeviceClass | str | None:
        """Return the class of this sensor."""
        return self.entity.binary_sensor_device_class
