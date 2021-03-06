"""
Support for Shinobi Video.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.shinobi/
"""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .component.helpers.const import *
from .component.models.shinobi_entity import ShinobiEntity
from .core.models.base_entity import async_setup_base_entry
from .core.models.entity_data import EntityData

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = [DOMAIN]

CURRENT_DOMAIN = DOMAIN_SWITCH


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up the Shinobi Video Switch."""
    await async_setup_base_entry(
        hass, config_entry, async_add_devices, CURRENT_DOMAIN, get_switch
    )


async def async_unload_entry(hass, config_entry):
    _LOGGER.info(f"Unload entry for {CURRENT_DOMAIN} domain: {config_entry}")

    return True


def get_switch(hass: HomeAssistant, entity: EntityData):
    switch = ShinobiSwitch()
    switch.initialize(hass, entity, CURRENT_DOMAIN)

    return switch


class ShinobiSwitch(SwitchEntity, ShinobiEntity):
    """Class for a Shinobi Video switch."""

    _attr_entity_category = EntityCategory.CONFIG

    @property
    def is_on(self) -> bool | None:
        """Return the boolean response if the node is on."""
        return self.entity.state == str(True)

    async def async_turn_on(self, **kwargs):
        """Turn device on."""
        await self.set_detector_mode(True)

    async def async_turn_off(self, **kwargs):
        """Turn device off."""
        await self.set_detector_mode(False)

    async def set_detector_mode(self, enabled: bool):
        if self.entity.binary_sensor_device_class == BinarySensorDeviceClass.MOTION:
            await self.ha.async_set_motion_detection(self.entity.id, enabled)
        else:
            await self.ha.async_set_sound_detection(self.entity.id, enabled)

    def turn_on(self, **kwargs) -> None:
        pass

    def turn_off(self, **kwargs) -> None:
        pass

    async def async_setup(self):
        pass
