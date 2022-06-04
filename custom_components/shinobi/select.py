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

from .component.helpers.const import *
from .component.models.shinobi_entity import ShinobiEntity
from .core.models.base_entity import async_setup_base_entry
from .core.models.entity_data import EntityData

DEPENDENCIES = [DOMAIN]

_LOGGER = logging.getLogger(__name__)

CURRENT_DOMAIN = DOMAIN_SELECT


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up the Shinobi Video Monitor Mode."""
    await async_setup_base_entry(
        hass, config_entry, async_add_devices, CURRENT_DOMAIN, get_select
    )


async def async_unload_entry(hass, config_entry):
    _LOGGER.info(f"Unload entry for {CURRENT_DOMAIN} domain: {config_entry}")

    return True


def get_select(hass: HomeAssistant, entity: EntityData):
    select = ShinobiSelect()
    select.initialize(hass, entity, CURRENT_DOMAIN)

    return select


@dataclass
class ShinobiVideoModeSelectDescription(SelectEntityDescription):
    """A class that describes select entities."""

    options: tuple = ()


SELECTOR_TYPES = {
    ATTR_MONITOR_MODE: ShinobiVideoModeSelectDescription(
        key=ATTR_MONITOR_MODE,
        name=ATTR_MONITOR_MODE,
        icon="mdi:cctv",
        device_class="shinobi__mode",
        options=tuple(ICON_MONITOR_MODES.keys()),
        entity_category=EntityCategory.CONFIG,
    ),
}


class ShinobiSelect(SelectEntity, ShinobiEntity, ABC):
    """ Shinobi Video Monitor Mode Control """

    entity_description = SELECTOR_TYPES[ATTR_MONITOR_MODE]
    _attr_options = list(entity_description.options)

    @property
    def current_option(self) -> str:
        """Return current lamp mode."""
        return self.entity.state

    @property
    def icon(self) -> str | None:
        """Return the icon to use in the frontend, if any."""
        icon = ICON_MONITOR_MODES.get(self.entity.state, "mdi:cctv")

        return icon

    async def async_select_option(self, option: str) -> None:
        """Select monitor mode."""
        await self.ha.async_set_monitor_mode(self.entity.id, option)
