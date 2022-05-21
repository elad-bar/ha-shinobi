"""
Support for Shinobi Video.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/camera.shinobi/
"""
from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
import logging

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .helpers.const import *
from .models.base_entity import BaseEntity, async_setup_base_entry
from .models.entity_data import EntityData

DEPENDENCIES = [DOMAIN]

_LOGGER = logging.getLogger(__name__)

CURRENT_DOMAIN = DOMAIN_SELECT


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up the Shinobi Video Camera."""
    await async_setup_base_entry(
        hass, config_entry, async_add_devices, CURRENT_DOMAIN, get_select
    )


async def async_unload_entry(hass, config_entry):
    _LOGGER.info(f"async_unload_entry {CURRENT_DOMAIN}: {config_entry}")

    return True


def get_select(hass: HomeAssistant, host: str, entity: EntityData):
    select = ShinobiSelect()
    select.initialize(hass, host, entity, CURRENT_DOMAIN)

    return select


@dataclass
class ShinobiVideoModeSelectDescription(SelectEntityDescription):
    """A class that describes select entities."""

    options: tuple = ()


SELECTOR_TYPES = {
    FEATURE_SET_CAMERA_MODE: ShinobiVideoModeSelectDescription(
        key=ATTR_CAMERA_MODE,
        name="Camera Mode",
        icon="mdi:cctv",
        device_class="shinobi__mode",
        options=tuple(ICON_CAMERA_MODES.keys()),
        entity_category=EntityCategory.CONFIG,
    ),
}


class ShinobiSelect(SelectEntity, BaseEntity, ABC):
    """ Shinobi Video Camera Mode Control """

    entity_description = SELECTOR_TYPES[FEATURE_SET_CAMERA_MODE]
    _attr_options = list(entity_description.options)

    @property
    def current_option(self) -> str:
        """Return current lamp mode."""
        return self.entity.state

    @property
    def icon(self) -> str | None:
        """Return the icon to use in the frontend, if any."""
        icon = ICON_CAMERA_MODES.get(self.entity.state, "mdi:cctv")

        return icon

    async def async_select_option(self, option: str) -> None:
        """Select lamp mode."""
        await self.entity_manager.async_set_camera_mode(self.entity.id, option)
