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

from cryptography.fernet import InvalidToken

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_registry import EntityRegistry, async_get
from homeassistant.helpers.event import async_track_time_interval

from ...component.api.shinobi_api import ShinobiApi
from ...component.api.shinobi_websocket import ShinobiWebSocket
from ...component.helpers.const import *
from ...component.models.monitor_data import MonitorData
from ...core.managers.device_manager import DeviceManager
from ...core.managers.entity_manager import EntityManager
from ...core.managers.password_manager import PasswordManager
from ...core.managers.storage_manager import StorageManager
from ...core.models.config_data import ConfigData, get_config_data_from_entry
from ..helpers.enums import ConnectivityStatus
from .event_manager import EventManager

_LOGGER = logging.getLogger(__name__)


class HomeAssistantManager:
    def __init__(self, hass: HomeAssistant, password_manager: PasswordManager):
        self._hass = hass
        self._password_manager = password_manager

        self._is_initialized = False
        self._is_updating = False

        self._entity_registry = None

        self._api: ShinobiApi | None = None
        self._ws: ShinobiWebSocket | None = None
        self.config_data: ConfigData | None = None

        self._storage_manager = StorageManager(self._hass)
        self._event_manager = EventManager(self._hass, self._update)
        self._entity_manager = EntityManager(self._hass, self)
        self._device_manager = DeviceManager(self._hass, self)

        self._entity_registry = async_get(self._hass)

        self._async_track_time_handlers = []
        self._last_heartbeat = None

        def _send_heartbeat(internal_now):
            self._last_heartbeat = internal_now

            self._hass.async_create_task(self._ws.async_send_heartbeat())

        self._send_heartbeat = _send_heartbeat

    @property
    def api(self) -> ShinobiApi:
        return self._api

    @property
    def ws(self) -> ShinobiWebSocket:
        return self._ws

    @property
    def entity_manager(self) -> EntityManager:
        return self._entity_manager

    @property
    def device_manager(self) -> DeviceManager:
        return self._device_manager

    @property
    def entity_registry(self) -> EntityRegistry:
        return self._entity_registry

    @property
    def storage_manager(self) -> StorageManager:
        return self._storage_manager

    @property
    def event_manager(self) -> EventManager:
        return self._event_manager

    @property
    def entry_id(self) -> str:
        return self.config_data.entry.entry_id

    @property
    def entry_title(self) -> str:
        return self.config_data.entry.title

    async def async_init(self, entry: ConfigEntry):
        try:
            self.config_data = get_config_data_from_entry(entry, self._password_manager.get)

            await self.event_manager.initialize()

            self._api = ShinobiApi(self._hass, self.config_data)
            self._ws = ShinobiWebSocket(self._hass, self._api, self.config_data, self._event_manager)

            self._hass.loop.create_task(self._async_load_platforms())

        except InvalidToken:
            error_message = "Encryption key got corrupted, please remove the integration and re-add it"

            _LOGGER.error(error_message)

            data = await self._storage_manager.async_load_from_store()
            data.key = None

            await self._storage_manager.async_save_to_store(data)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to async_init, error: {ex}, line: {line_number}")

    async def _async_load_platforms(self):
        load = self._hass.config_entries.async_forward_entry_setup

        for domain in PLATFORMS:
            await load(self.config_data.entry, domain)

        self._is_initialized = True

        await self.async_update_entry()

    def _update_entities(self, now):
        self._hass.async_create_task(self.async_update(now))

    async def async_update_entry(self, entry: ConfigEntry = None):
        entry_changed = entry is not None

        if entry_changed:
            self.config_data = get_config_data_from_entry(entry, self._password_manager.get)

            _LOGGER.info(f"Handling ConfigEntry load: {entry.as_dict()}")

        else:
            entry = self.config_data.entry

            remove_async_track_time = async_track_time_interval(
                self._hass, self._update_entities, SCAN_INTERVAL
            )

            remove_async_heartbeat_track_time = async_track_time_interval(
                self._hass, self._send_heartbeat, HEARTBEAT_INTERVAL_SECONDS
            )

            self._async_track_time_handlers.append(remove_async_track_time)
            self._async_track_time_handlers.append(remove_async_heartbeat_track_time)

            _LOGGER.info(f"Handling ConfigEntry change: {entry.as_dict()}")

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

    async def async_unload(self):
        _LOGGER.info(f"HA was stopped")

        await self.api.terminate()
        await self.ws.terminate()

    async def async_remove(self, entry: ConfigEntry):
        _LOGGER.info(f"Removing current integration - {entry.title}")

        for handler in self._async_track_time_handlers:
            if handler is not None:
                handler()

        self._async_track_time_handlers.clear()

        self.event_manager.terminate()

        await self.ws.terminate()

        unload = self._hass.config_entries.async_forward_entry_unload

        for domain in PLATFORMS:
            await unload(entry, domain)

        await self._device_manager.async_remove()

        _LOGGER.info(f"Current integration ({entry.title}) removed")

    def _update(self):
        self._load_entities()

        self.entity_manager.update()

        self._hass.async_create_task(self.dispatch_all())

    async def async_update(self, event_time):
        if not self._is_initialized:
            _LOGGER.info(f"NOT INITIALIZED - Failed updating @{event_time}")
            return

        try:
            if self._is_updating:
                _LOGGER.debug(f"Skip updating @{event_time}")
                return

            _LOGGER.debug(f"Updating @{event_time}")

            self._is_updating = True

            await self._api.async_update()

            self.device_manager.generate_device(f"{self.entry_title} Server", "System")

            for monitor_id in self._api.monitors:
                monitor = self._api.monitors.get(monitor_id)
                device_name = self._get_monitor_device_name(monitor)

                self.device_manager.generate_device(device_name, "Camera")

            self._update()
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to async_update, Error: {ex}, Line: {line_number}")

        self._is_updating = False

    def _get_monitor_device_name(self, monitor: MonitorData):
        device_name = f"{self.entry_title} {monitor.name} ({monitor.id})"

        return device_name

    async def delete_entity(self, domain, name):
        try:
            available_domains = self.entity_manager.available_domains
            domain_data = self.entity_manager.get_domain_data(domain)

            entity = domain_data.get_entity(name)
            device_name = entity.device_name
            unique_id = entity.unique_id

            domain_data.delete_entity(name)

            device_in_use = False

            for domain_name in available_domains:
                if domain_name != domain:
                    domain_data = self.entity_manager.get_domain_data(domain_name)

                    if device_name in domain_data.entities:
                        device_in_use = True
                        break

            entity_id = self.entity_registry.async_get_entity_id(
                domain, DOMAIN, unique_id
            )
            self.entity_registry.async_remove(entity_id)

            if not device_in_use:
                await self.device_manager.delete_device(device_name)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to delete_entity, Error: {ex}, Line: {line_number}")

    async def dispatch_all(self):
        if not self._is_initialized:
            _LOGGER.info("NOT INITIALIZED - Failed discovering components")
            return

        for domain in PLATFORMS:
            signal = PLATFORMS.get(domain)

            async_dispatcher_send(self._hass, signal)

    async def async_set_monitor_mode(self, monitor_id: str, mode: str):
        await self.api.async_set_monitor_mode(monitor_id, mode)

        await self.async_update(datetime.datetime.now)

    async def async_set_motion_detection(self, monitor_id: str, enabled: bool):
        await self.api.async_set_motion_detection(monitor_id, enabled)

        await self.async_update(datetime.datetime.now)

    async def async_set_sound_detection(self, monitor_id: str, enabled: bool):
        await self.api.async_set_sound_detection(monitor_id, enabled)

        await self.async_update(datetime.datetime.now)

    def _load_entities(self):
        for monitor_id in self.api.monitors:
            monitor = self.api.monitors.get(monitor_id)
            device = self._get_monitor_device_name(monitor)

            self._load_camera_component(monitor, device)
            self._load_select_component(monitor, device)

            self._load_binary_sensor_entity(monitor, BinarySensorDeviceClass.SOUND, device)
            self._load_binary_sensor_entity(monitor, BinarySensorDeviceClass.MOTION, device)

            self._load_switch_entity(monitor, BinarySensorDeviceClass.SOUND, device)
            self._load_switch_entity(monitor, BinarySensorDeviceClass.MOTION, device)

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
