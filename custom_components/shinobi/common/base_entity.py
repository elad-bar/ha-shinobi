import logging
import sys
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from ..managers.coordinator import Coordinator
from .consts import ADD_COMPONENT_SIGNALS, DOMAIN
from .entity_descriptions import IntegrationEntityDescription, get_entity_descriptions
from .monitor_data import MonitorData

_LOGGER = logging.getLogger(__name__)


async def async_setup_base_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    platform: Platform,
    entity_type: type,
    async_add_entities,
):
    @callback
    def _async_handle_device(entry_id: str, monitor: MonitorData | None = None):
        if entry.entry_id != entry_id:
            return

        try:
            coordinator = hass.data[DOMAIN][entry.entry_id]

            entity_descriptions = get_entity_descriptions(platform, monitor)

            entities = [
                entity_type(hass, entity_description, coordinator, monitor)
                for entity_description in entity_descriptions
            ]

            _LOGGER.debug(f"Setting up {platform} entities: {entities}")

            async_add_entities(entities, True)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to initialize {platform}, Error: {ex}, Line: {line_number}"
            )

    for add_component_signal in ADD_COMPONENT_SIGNALS:
        _LOGGER.info(platform)
        _LOGGER.info(add_component_signal)

        entry.async_on_unload(
            async_dispatcher_connect(hass, add_component_signal, _async_handle_device)
        )


class IntegrationBaseEntity(CoordinatorEntity):
    _entity_description: IntegrationEntityDescription

    def __init__(
        self,
        hass: HomeAssistant,
        entity_description: IntegrationEntityDescription,
        coordinator: Coordinator,
        monitor: MonitorData | None,
    ):
        super().__init__(coordinator)

        try:
            _LOGGER.info(entity_description)

            self.hass = hass
            self.monitor_id = None

            if monitor is None:
                device_info = coordinator.get_server_device_info()

            else:
                self.monitor_id = monitor.id
                device_info = coordinator.get_monitor_device_info(monitor.id)

            identifiers = device_info.get("identifiers")
            identifier = list(identifiers)[0][1]

            entity_name = coordinator.config_manager.get_entity_name(
                entity_description, device_info
            )

            slugify_name = slugify(entity_name)

            unique_id = slugify(
                f"{entity_description.platform}_{identifier}_{slugify_name}"
            )

            self.entity_description = entity_description
            self._entity_description = entity_description

            self._attr_device_info = device_info
            self._attr_name = entity_name
            self._attr_unique_id = unique_id

            self._data = {}

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to initialize {entity_description}, Error: {ex}, Line: {line_number}"
            )

    @property
    def _local_coordinator(self) -> Coordinator:
        return self.coordinator

    @property
    def data(self) -> dict | None:
        return self._data

    async def async_execute_device_action(self, key: str, *kwargs: Any):
        async_device_action = self._local_coordinator.get_device_action(
            self._entity_description, key
        )

        await async_device_action(self._entity_description, self.monitor_id, *kwargs)

        await self.coordinator.async_request_refresh()

    def update_component(self, data):
        pass

    def _handle_coordinator_update(self) -> None:
        """Fetch new state parameters for the sensor."""
        try:
            new_data = self._local_coordinator.get_data(
                self._entity_description, self.monitor_id
            )

            if self._data != new_data:
                _LOGGER.debug(f"Data for {self.unique_id}: {new_data}")

                self.update_component(new_data)

                self._data = new_data

                self.async_write_ha_state()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to update {self.unique_id}, Error: {ex}, Line: {line_number}"
            )
