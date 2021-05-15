"""
Support for Shinobi Video binary sensors.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/binary_sensor.shinobi/
"""
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant

from .helpers.const import *
from .models.base_entity import BaseEntity, async_setup_base_entry
from .models.entity_data import EntityData

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = [DOMAIN, "mqtt"]

CURRENT_DOMAIN = DOMAIN_BINARY_SENSOR


def get_binary_sensor(hass: HomeAssistant, host: str, entity: EntityData):
    binary_sensor = BaseBinarySensor()
    binary_sensor.initialize(hass, host, entity, CURRENT_DOMAIN)

    return binary_sensor


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up the Shinobi Video Binary Sensor."""
    await async_setup_base_entry(
        hass, config_entry, async_add_devices, CURRENT_DOMAIN, get_binary_sensor
    )


async def async_unload_entry(hass, config_entry):
    _LOGGER.info(f"async_unload_entry {CURRENT_DOMAIN}: {config_entry}")

    return True


class BaseBinarySensor(BinarySensorEntity, BaseEntity):
    """Representation a binary sensor that is updated by MQTT."""

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self.entity.state == STATE_ON

    @property
    def device_class(self):
        """Return the class of this sensor."""
        return self.entity.device_class

    @property
    def force_update(self):
        """Force update."""
        return DEFAULT_FORCE_UPDATE

    async def async_added_to_hass_local(self):
        _LOGGER.info(f"Added new {self.name}")

    def _immediate_update(self, previous_state: bool):
        is_on = self.entity.state == STATE_ON
        was_changed = self.state != previous_state

        if was_changed:
            _LOGGER.debug(
                f"{self.name} updated from {previous_state} to {self.state}"
            )

        if not is_on or was_changed:
            super()._immediate_update(previous_state)
