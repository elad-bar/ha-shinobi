"""
Support for Shinobi Video.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/shinobi/
"""
from __future__ import annotations

import asyncio
import datetime
import logging
import sys

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ...component.api.shinobi_api import ShinobiApi
from ...component.api.shinobi_websocket import ShinobiWebSocket
from ...component.helpers.const import *
from ...component.helpers.enums import ConnectivityStatus
from ...component.managers.event_manager import ShinobiEventManager
from ...component.models.monitor_data import MonitorData
from ...configuration.managers.configuration_manager import (
    ConfigurationManager,
    async_get_configuration_manager,
)
from ...configuration.models.config_data import ConfigData
from ...core.managers.home_assistant import HomeAssistantManager

_LOGGER = logging.getLogger(__name__)


class ShinobiHomeAssistantManager(HomeAssistantManager):
    def __init__(self, hass: HomeAssistant):
        super().__init__(hass, SCAN_INTERVAL, HEARTBEAT_INTERVAL_SECONDS)

        self._api: ShinobiApi | None = None
        self._ws: ShinobiWebSocket | None = None
        self._config_manager: ConfigurationManager | None = None

        self._event_manager = ShinobiEventManager(self._hass, super().update)

    @property
    def api(self) -> ShinobiApi:
        return self._api

    @property
    def ws(self) -> ShinobiWebSocket:
        return self._ws

    @property
    def event_manager(self) -> ShinobiEventManager:
        return self._event_manager

    @property
    def config_data(self) -> ConfigData:
        return self._config_manager.get(self.entry_id)

    async def async_send_heartbeat(self):
        """ Must be implemented to be able to send heartbeat to API """
        await self._ws.async_send_heartbeat()

    async def async_component_initialize(self, entry: ConfigEntry):
        try:
            self._config_manager = async_get_configuration_manager(self._hass)
            await self._config_manager.load(entry)

            await self.event_manager.initialize()

            self._api = ShinobiApi(self._hass, self.config_data)
            self._ws = ShinobiWebSocket(self._hass, self._api, self.config_data, self._event_manager)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to async_component_initialize, error: {ex}, line: {line_number}")

    async def async_initialize_data_providers(self, entry: ConfigEntry | None = None):
        await self.api.initialize(self.config_data)

        if self.api.status == ConnectivityStatus.Connected:
            ws_version = await self.api.get_socket_io_version()

            if self.ws.version != ws_version:
                self.ws.version = ws_version

            await self.async_update(datetime.datetime.now())

            while not self.ws.is_aborted:
                await self.ws.initialize()

                if not self.ws.is_aborted:
                    await asyncio.sleep(RECONNECT_INTERVAL)

    async def async_stop_data_providers(self):
        self.event_manager.terminate()
        await self.api.terminate()
        await self.ws.terminate()

    async def async_update_data_providers(self):
        try:
            await self._api.async_update()

            self.device_manager.generate_device(f"{self.entry_title} Server", "System")

            for monitor_id in self._api.monitors:
                monitor = self._api.monitors.get(monitor_id)
                device_name = self._get_monitor_device_name(monitor)

                self.device_manager.generate_device(device_name, "Camera")
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to async_update_data_providers, Error: {ex}, Line: {line_number}")

    def load_entities(self):
        for monitor_id in self.api.monitors:
            monitor = self.api.monitors.get(monitor_id)
            device = self._get_monitor_device_name(monitor)

            self._load_camera_component(monitor, device)
            self._load_select_component(monitor, device)

            self._load_binary_sensor_entity(monitor, BinarySensorDeviceClass.SOUND, device)
            self._load_binary_sensor_entity(monitor, BinarySensorDeviceClass.MOTION, device)

            self._load_switch_entity(monitor, BinarySensorDeviceClass.SOUND, device)
            self._load_switch_entity(monitor, BinarySensorDeviceClass.MOTION, device)

    def _get_monitor_device_name(self, monitor: MonitorData):
        device_name = f"{self.entry_title} {monitor.name} ({monitor.id})"

        return device_name

    async def async_set_monitor_mode(self, monitor_id: str, mode: str):
        await self.api.async_set_monitor_mode(monitor_id, mode)

        await self.async_update(datetime.datetime.now)

    async def async_set_motion_detection(self, monitor_id: str, enabled: bool):
        await self.api.async_set_motion_detection(monitor_id, enabled)

        await self.async_update(datetime.datetime.now)

    async def async_set_sound_detection(self, monitor_id: str, enabled: bool):
        await self.api.async_set_sound_detection(monitor_id, enabled)

        await self.async_update(datetime.datetime.now)

    def _load_camera_component(self, monitor: MonitorData, device: str):
        try:
            entity_name = f"{self.entry_title} {monitor.name}"

            if monitor.jpeg_api_enabled:
                use_original_stream = self.config_data.use_original_stream

                snapshot = self.api.build_url(monitor.snapshot)

                stream_source = None

                if not use_original_stream:
                    for stream in monitor.streams:
                        if stream is not None:
                            stream_source = self.api.build_url(stream)
                            break

                if use_original_stream or stream_source is None:
                    stream_source = monitor.original_stream

                attributes = {
                    ATTR_FRIENDLY_NAME: entity_name,
                    CONF_STREAM_SOURCE: stream_source,
                    CONF_STILL_IMAGE_URL: snapshot
                }

                for key in MONITOR_ATTRIBUTES:
                    key_name = MONITOR_ATTRIBUTES[key]
                    attributes[key_name] = monitor.details.get(key, "N/A")

                monitor_details = monitor.details.get(ATTR_MONITOR_DETAILS, {})

                for key in MONITOR_DETAILS_ATTRIBUTES:
                    key_name = MONITOR_DETAILS_ATTRIBUTES[key]
                    attributes[key_name] = monitor_details.get(key, "N/A")

                entity = self.entity_manager.get(DOMAIN_CAMERA, entity_name)
                created = entity is None

                if created:
                    entity = self.entity_manager.get_empty_entity(self.entry_id)

                    entity.id = monitor.id
                    entity.name = entity_name
                    entity.icon = DEFAULT_ICON
                    entity.domain = DOMAIN_CAMERA

                data = {
                    "state": (entity.state, monitor.mode),
                    "attributes": (entity.attributes, attributes),
                    "device_name": (entity.device_name, device)
                }

                if created or self.entity_manager.compare_data(entity, data):
                    entity.state = monitor.mode
                    entity.attributes = attributes
                    entity.device_name = device

                    entity.set_created_or_updated(created)

                self.entity_manager.set(entity, [monitor.disabled])

            else:
                _LOGGER.warning(f"JPEG API is not enabled for {monitor.name}, Monitor will not be created")

        except Exception as ex:
            self.log_exception(ex, f"Failed to load camera for {monitor}")

    def _load_select_component(self, monitor: MonitorData, device: str):
        try:
            entity_name = f"{self.entry_title} {monitor.name} {ATTR_MONITOR_MODE}"

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name,
            }

            entity = self.entity_manager.get(DOMAIN_SELECT, entity_name)
            created = entity is None

            if created:
                entity = self.entity_manager.get_empty_entity(self.entry_id)

                entity.id = monitor.id
                entity.name = entity_name
                entity.attributes = attributes
                entity.icon = DEFAULT_ICON
                entity.domain = DOMAIN_SELECT

            data = {
                "state": (entity.state, monitor.mode),
                "device_name": (entity.device_name, device),
            }

            if created or self.entity_manager.compare_data(entity, data):
                entity.device_name = device
                entity.state = monitor.mode

                entity.set_created_or_updated(created)

            self.entity_manager.set(entity)

        except Exception as ex:
            self.log_exception(ex, f"Failed to load select for {monitor}")

    def _load_binary_sensor_entity(
            self,
            monitor: MonitorData,
            sensor_type: BinarySensorDeviceClass,
            device: str
    ):
        try:
            entity_name = f"{self.entry_title} {monitor.name} {sensor_type.capitalize()}"

            state_topic = f"{self.api.group_id}/{monitor.id}"

            state = STATE_OFF
            event_state = TRIGGER_DEFAULT

            if self.event_manager is not None:
                event_state = self.event_manager.get(state_topic, sensor_type)
                state = event_state.get(TRIGGER_STATE, STATE_OFF)

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name
            }

            for attr in BINARY_SENSOR_ATTRIBUTES:
                if attr in event_state:
                    attributes[attr] = event_state.get(attr)

            entity = self.entity_manager.get(DOMAIN_BINARY_SENSOR, entity_name)
            created = entity is None

            is_sound = sensor_type == BinarySensorDeviceClass.SOUND
            detector_active = monitor.has_audio_detector if is_sound else monitor.has_motion_detector

            if created:
                entity = self.entity_manager.get_empty_entity(self.entry_id)

                entity.id = monitor.id
                entity.name = entity_name
                entity.icon = DEFAULT_ICON
                entity.binary_sensor_device_class = sensor_type
                entity.domain = DOMAIN_BINARY_SENSOR

            data = {
                "state": (entity.state, str(state)),
                "attributes": (entity.attributes, attributes),
                "device_name": (entity.device_name, device),
            }

            if created or self.entity_manager.compare_data(entity, data):
                entity.state = state
                entity.attributes = attributes
                entity.device_name = device

                entity.set_created_or_updated(created)

            self.entity_manager.set(entity, [monitor.disabled, not detector_active])

        except Exception as ex:
            self.log_exception(
                ex, f"Failed to load binary sensor for {monitor.name}"
            )

    def _load_switch_entity(
            self,
            monitor: MonitorData,
            sensor_type: BinarySensorDeviceClass,
            device: str
    ):
        try:
            entity_name = f"{self.entry_title} {monitor.name} {sensor_type.capitalize()}"

            state = monitor.has_motion_detector \
                if sensor_type == BinarySensorDeviceClass.MOTION \
                else monitor.has_audio_detector

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name
            }

            entity = self.entity_manager.get(DOMAIN_SWITCH, entity_name)
            created = entity is None

            is_sound = sensor_type == BinarySensorDeviceClass.SOUND

            if created:
                entity = self.entity_manager.get_empty_entity(self.entry_id)

                entity.id = monitor.id
                entity.name = entity_name
                entity.icon = DEFAULT_ICON
                entity.binary_sensor_device_class = sensor_type
                entity.domain = DOMAIN_SWITCH

            data = {
                "state": (entity.state, str(state)),
                "attributes": (entity.attributes, attributes),
                "device_name": (entity.device_name, device),
            }

            if created or self.entity_manager.compare_data(entity, data):
                entity.state = str(state)
                entity.attributes = attributes
                entity.device_name = device

                entity.set_created_or_updated(created)

            self.entity_manager.set(entity, [monitor.disabled, is_sound and not monitor.has_audio])
        except Exception as ex:
            self.log_exception(
                ex, f"Failed to load switch for {monitor.name}"
            )

    @staticmethod
    def log_exception(ex, message):
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno

        _LOGGER.error(f"{message}, Error: {str(ex)}, Line: {line_number}")
