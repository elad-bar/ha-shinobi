"""
Support for Shinobi Video.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/shinobi/
"""
from __future__ import annotations

from asyncio import sleep
from datetime import timedelta
import logging
import sys

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.components.camera import CameraEntityDescription
from homeassistant.components.homeassistant import SERVICE_RELOAD_CONFIG_ENTRY
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.switch import SwitchDeviceClass, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_FRIENDLY_NAME, STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from ...configuration.helpers.const import DEFAULT_NAME, DOMAIN
from ...configuration.managers.configuration_manager import ConfigurationManager
from ...configuration.models.config_data import ConfigData
from ...core.helpers.const import (
    ACTION_CORE_ENTITY_DISABLE_MOTION_DETECTION,
    ACTION_CORE_ENTITY_ENABLE_MOTION_DETECTION,
    ACTION_CORE_ENTITY_SELECT_OPTION,
    ACTION_CORE_ENTITY_TURN_OFF,
    ACTION_CORE_ENTITY_TURN_ON,
    ATTR_MODE_RECORD,
    CONF_STILL_IMAGE_URL,
    CONF_STREAM_SOURCE,
    DOMAIN_BINARY_SENSOR,
    DOMAIN_CAMERA,
    DOMAIN_SELECT,
    DOMAIN_SWITCH,
    ENTITY_CONFIG_ENTRY_ID,
    HA_NAME,
)
from ...core.helpers.enums import ConnectivityStatus
from ...core.managers.home_assistant import HomeAssistantManager
from ...core.models.entity_data import EntityData
from ..api.api import IntegrationAPI
from ..api.storage_api import StorageAPI
from ..api.websocket import IntegrationWS
from ..helpers.const import (
    ATTR_MONITOR_DETAILS,
    ATTR_MONITOR_ID,
    ATTR_MONITOR_MODE,
    BINARY_SENSOR_ATTRIBUTES,
    DEFAULT_ICON,
    HEARTBEAT_INTERVAL_SECONDS,
    ICON_MONITOR_MODES,
    MONITOR_ATTRIBUTES,
    MONITOR_DETAILS_ATTRIBUTES,
    MONITOR_MODE_RECORD,
    SCAN_INTERVAL,
    TRIGGER_INTERVAL,
    TRIGGER_STATE,
    WS_RECONNECT_INTERVAL,
)
from ..models.monitor_data import MonitorData

_LOGGER = logging.getLogger(__name__)


class ShinobiHomeAssistantManager(HomeAssistantManager):
    def __init__(self, hass: HomeAssistant):
        super().__init__(hass, SCAN_INTERVAL, HEARTBEAT_INTERVAL_SECONDS)

        self._api: IntegrationAPI = IntegrationAPI(
            self._hass, self._api_data_changed, self._api_status_changed
        )
        self._ws: IntegrationWS = IntegrationWS(
            self._hass, self._ws_data_changed, self._ws_status_changed
        )
        self._storage_api = StorageAPI(self._hass)
        self._config_manager: ConfigurationManager | None = None

    @property
    def api(self) -> IntegrationAPI:
        return self._api

    @property
    def ws(self) -> IntegrationWS:
        return self._ws

    @property
    def storage_api(self) -> StorageAPI:
        return self._storage_api

    @property
    def config_data(self) -> ConfigData:
        return self._config_manager.get(self.entry_id)

    async def async_send_heartbeat(self):
        """Must be implemented to be able to send heartbeat to API"""
        await self.ws.async_send_heartbeat()

    async def _api_data_changed(self):
        api_connected = self.api.status == ConnectivityStatus.Connected
        ws_connected = self.ws.status == ConnectivityStatus.Connected

        if api_connected and ws_connected:
            await self.api.async_repair_monitors()

    async def _ws_data_changed(self):
        ws_connected = self.ws.status == ConnectivityStatus.Connected

        _LOGGER.debug(f"WebSockets data changed, Connection: {ws_connected}")

    async def _api_status_changed(self, status: ConnectivityStatus):
        _LOGGER.info(
            f"API Status changed to {status.name}, WS Status: {self.ws.status.name}"
        )

        if status == ConnectivityStatus.Connected:
            await self.api.async_update()

            await self.ws.update_api_data(self.api.data)

            self._update_entities(None)

            await self.ws.initialize(self.config_data)

        elif status == ConnectivityStatus.Failed:
            if self.ws.status == ConnectivityStatus.Connected:
                await self.ws.terminate()

            ws_reconnect_interval = WS_RECONNECT_INTERVAL.total_seconds()
            await sleep(ws_reconnect_interval)

            _LOGGER.info(f"Attempt to reconnect after {ws_reconnect_interval} seconds")

            await self.api.initialize(self.config_data)

        elif status == ConnectivityStatus.Disconnected:
            if self.ws.status == ConnectivityStatus.Connected:
                await self.ws.terminate()

    async def _ws_status_changed(self, status: ConnectivityStatus):
        _LOGGER.info(
            f"WS Status changed to {status.name}, API Status: {self.api.status.name}"
        )

        api_connected = self.api.status == ConnectivityStatus.Connected
        ws_connected = status == ConnectivityStatus.Connected
        ws_reconnect = status in [
            ConnectivityStatus.NotConnected,
            ConnectivityStatus.Failed,
        ]

        self._can_load_components = ws_connected

        if ws_reconnect and api_connected:
            await sleep(WS_RECONNECT_INTERVAL.total_seconds())

            await self.ws.initialize()

    async def async_component_initialize(self, entry: ConfigEntry):
        try:
            self._config_manager = ConfigurationManager(self._hass, self.api)
            await self._config_manager.load(entry)

            update_entities_interval = timedelta(
                seconds=TRIGGER_INTERVAL.total_seconds()
            )
            update_api_interval = timedelta(seconds=SCAN_INTERVAL.total_seconds())

            self.update_intervals(update_entities_interval, update_api_interval)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to async_component_initialize, error: {ex}, line: {line_number}"
            )

    async def async_initialize_data_providers(self):
        await self.storage_api.initialize(self.config_data)
        await self.api.initialize(self.config_data)

    async def async_stop_data_providers(self):
        await self.api.terminate()

    async def async_update_data_providers(self):
        try:
            await self.api.async_update()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to async_update_data_providers, Error: {ex}, Line: {line_number}"
            )

    def load_devices(self):
        server_name = f"{self.entry_title} Server"

        server_device = self.device_manager.get(server_name)

        server_device_info = {
            "identifiers": {(DEFAULT_NAME, server_name)},
            "name": server_name,
            "manufacturer": DEFAULT_NAME,
            "model": "Server",
        }

        if server_device is None or server_device != server_device_info:
            self.device_manager.set(server_name, server_device_info)

            _LOGGER.info(f"Created device {server_device}, Data: {server_device_info}")

        for monitor_id in self._api.monitors:
            monitor = self._api.monitors.get(monitor_id)
            device_name = self.get_monitor_device_name(monitor)
            monitor_device = self.device_manager.get(device_name)

            monitor_device_info = {
                "identifiers": {(DEFAULT_NAME, device_name)},
                "name": device_name,
                "manufacturer": DEFAULT_NAME,
                "model": "Camera",
            }

            if monitor_device is None or monitor_device != monitor_device_info:
                self.device_manager.set(device_name, monitor_device_info)

                _LOGGER.info(
                    f"Created device {device_name}, Data: {monitor_device_info}"
                )

    def load_entities(self):
        server_name = f"{self.entry_title} Server"

        self._load_original_stream_switch_entity(server_name)

        for monitor_id in self.api.monitors:
            monitor = self.api.monitors.get(monitor_id)
            device = self.get_monitor_device_name(monitor)

            if not monitor.jpeg_api_enabled:
                _LOGGER.warning(
                    f"JPEG API is not enabled for {monitor.name}, Camera will not be created"
                )

            self._load_camera_component(monitor, device)
            self._load_select_component(monitor, device)

            self._load_binary_sensor_entity(
                monitor, BinarySensorDeviceClass.SOUND, device
            )
            self._load_binary_sensor_entity(
                monitor, BinarySensorDeviceClass.MOTION, device
            )

            self._load_switch_entity(monitor, BinarySensorDeviceClass.SOUND, device)
            self._load_switch_entity(monitor, BinarySensorDeviceClass.MOTION, device)

    def get_monitor_device_name(self, monitor: MonitorData):
        device_name = f"{self.entry_title} {monitor.name} ({monitor.id})"

        return device_name

    def _load_camera_component(self, monitor: MonitorData, device_name: str):
        try:
            entity_name = f"{self.entry_title} {monitor.name}"

            use_original_stream = self.storage_api.use_original_stream

            snapshot = monitor.snapshot

            if snapshot.startswith("/"):
                snapshot = snapshot[1:]

            snapshot = self.api.build_url(f"{{base_url}}{snapshot}")

            stream_source = None

            if not use_original_stream:
                for stream in monitor.streams:
                    if stream is not None:
                        if stream.startswith("/"):
                            stream = stream[1:]

                        stream_source = self.api.build_url(f"{{base_url}}{stream}")
                        break

            if use_original_stream or stream_source is None:
                stream_source = monitor.original_stream

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name,
                CONF_STREAM_SOURCE: stream_source,
                CONF_STILL_IMAGE_URL: snapshot,
            }

            for key in MONITOR_ATTRIBUTES:
                key_name = MONITOR_ATTRIBUTES[key]
                attributes[key_name] = monitor.details.get(key, "N/A")

            monitor_details = monitor.details.get(ATTR_MONITOR_DETAILS, {})
            monitor_details[ATTR_MODE_RECORD] = MONITOR_MODE_RECORD
            monitor_details[ATTR_MONITOR_ID] = monitor.id

            for key in MONITOR_DETAILS_ATTRIBUTES:
                key_name = MONITOR_DETAILS_ATTRIBUTES[key]
                attributes[key_name] = monitor_details.get(key, "N/A")

            unique_id = EntityData.generate_unique_id(DOMAIN_CAMERA, entity_name)

            entity_description = CameraEntityDescription(
                key=unique_id, name=entity_name, icon=DEFAULT_ICON
            )

            self.set_action(
                unique_id,
                ACTION_CORE_ENTITY_ENABLE_MOTION_DETECTION,
                self._enable_motion_detection,
            )
            self.set_action(
                unique_id,
                ACTION_CORE_ENTITY_DISABLE_MOTION_DETECTION,
                self._disable_motion_detection,
            )

            self.entity_manager.set_entity(
                DOMAIN_CAMERA,
                self.entry_id,
                monitor.mode,
                attributes,
                device_name,
                entity_description,
                destructors=[monitor.disabled, not monitor.jpeg_api_enabled],
                details=monitor_details,
            )

        except Exception as ex:
            self.log_exception(ex, f"Failed to load camera for {monitor}")

    def _load_select_component(self, monitor: MonitorData, device_name: str):
        try:
            entity_name = f"{self.entry_title} {monitor.name} {ATTR_MONITOR_MODE}"

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name,
            }

            unique_id = EntityData.generate_unique_id(DOMAIN_SELECT, entity_name)

            icon = ICON_MONITOR_MODES.get(monitor.mode, "mdi:cctv")

            entity_description = SelectEntityDescription(
                key=unique_id,
                name=entity_name,
                icon=icon,
                device_class=f"{DOMAIN}__{ATTR_MONITOR_MODE}",
                options=list(ICON_MONITOR_MODES.keys()),
                entity_category=EntityCategory.CONFIG,
            )

            monitor_details = {ATTR_MONITOR_ID: monitor.id}

            self.set_action(
                unique_id, ACTION_CORE_ENTITY_SELECT_OPTION, self._set_monitor_mode
            )

            self.entity_manager.set_entity(
                DOMAIN_SELECT,
                self.entry_id,
                monitor.mode,
                attributes,
                device_name,
                entity_description,
                details=monitor_details,
            )

        except Exception as ex:
            self.log_exception(ex, f"Failed to load select for {monitor}")

    def _load_binary_sensor_entity(
        self,
        monitor: MonitorData,
        sensor_type: BinarySensorDeviceClass,
        device_name: str,
    ):
        try:
            entity_name = (
                f"{self.entry_title} {monitor.name} {sensor_type.capitalize()}"
            )

            state_topic = f"{self.api.group_id}/{monitor.id}"

            event_state = self.ws.get_data(state_topic, sensor_type)
            state = event_state.get(TRIGGER_STATE, STATE_OFF)

            attributes = {ATTR_FRIENDLY_NAME: entity_name}

            for attr in BINARY_SENSOR_ATTRIBUTES:
                if attr in event_state:
                    attributes[attr] = event_state.get(attr)

            is_sound = sensor_type == BinarySensorDeviceClass.SOUND
            detector_active = (
                monitor.has_audio_detector if is_sound else monitor.has_motion_detector
            )

            unique_id = EntityData.generate_unique_id(DOMAIN_BINARY_SENSOR, entity_name)

            entity_description = BinarySensorEntityDescription(
                key=unique_id, name=entity_name, device_class=sensor_type
            )

            monitor_details = {ATTR_MONITOR_ID: monitor.id}

            self.entity_manager.set_entity(
                DOMAIN_BINARY_SENSOR,
                self.entry_id,
                state,
                attributes,
                device_name,
                entity_description,
                destructors=[monitor.disabled, not detector_active],
                details=monitor_details,
            )

        except Exception as ex:
            self.log_exception(ex, f"Failed to load binary sensor for {monitor.name}")

    def _load_switch_entity(
        self,
        monitor: MonitorData,
        sensor_type: BinarySensorDeviceClass,
        device_name: str,
    ):
        try:
            entity_name = (
                f"{self.entry_title} {monitor.name} {sensor_type.capitalize()}"
            )

            state = (
                monitor.has_motion_detector
                if sensor_type == BinarySensorDeviceClass.MOTION
                else monitor.has_audio_detector
            )

            attributes = {ATTR_FRIENDLY_NAME: entity_name}

            is_sound = sensor_type == BinarySensorDeviceClass.SOUND

            unique_id = EntityData.generate_unique_id(DOMAIN_SWITCH, entity_name)

            icon = None

            if sensor_type == BinarySensorDeviceClass.SOUND:
                icon = "mdi:music-note" if state else "mdi:music-note-off"
                self.set_action(
                    unique_id, ACTION_CORE_ENTITY_TURN_ON, self._enable_sound_detection
                )
                self.set_action(
                    unique_id,
                    ACTION_CORE_ENTITY_TURN_OFF,
                    self._disable_sound_detection,
                )

            elif sensor_type == BinarySensorDeviceClass.MOTION:
                icon = "mdi:motion-sensor" if state else "mdi:motion-sensor-off"
                self.set_action(
                    unique_id, ACTION_CORE_ENTITY_TURN_ON, self._enable_motion_detection
                )
                self.set_action(
                    unique_id,
                    ACTION_CORE_ENTITY_TURN_OFF,
                    self._disable_motion_detection,
                )

            entity_description = SwitchEntityDescription(
                key=unique_id,
                name=entity_name,
                icon=icon,
                device_class=SwitchDeviceClass.SWITCH,
                entity_category=EntityCategory.CONFIG,
            )

            monitor_details = {ATTR_MONITOR_ID: monitor.id}

            self.entity_manager.set_entity(
                DOMAIN_SWITCH,
                self.entry_id,
                state,
                attributes,
                device_name,
                entity_description,
                destructors=[monitor.disabled, is_sound and not monitor.has_audio],
                details=monitor_details,
            )

        except Exception as ex:
            self.log_exception(ex, f"Failed to load switch for {monitor.name}")

    def _load_original_stream_switch_entity(self, device_name: str):
        try:
            entity_name = f"{self.entry_title} Original Stream"

            state = self.storage_api.use_original_stream

            attributes = {ATTR_FRIENDLY_NAME: entity_name}

            unique_id = EntityData.generate_unique_id(DOMAIN_SWITCH, entity_name)

            icon = "mdi:cctv" if state else "mdi:server-network"

            entity_description = SwitchEntityDescription(
                key=unique_id,
                name=entity_name,
                icon=icon,
                entity_category=EntityCategory.CONFIG,
            )

            self.set_action(
                unique_id, ACTION_CORE_ENTITY_TURN_ON, self._use_original_stream
            )
            self.set_action(
                unique_id, ACTION_CORE_ENTITY_TURN_OFF, self._use_default_stream
            )

            self.entity_manager.set_entity(
                DOMAIN_SWITCH,
                self.entry_id,
                state,
                attributes,
                device_name,
                entity_description,
            )

        except Exception as ex:
            self.log_exception(ex, "Failed to load switch for Original Stream")

    async def _set_monitor_mode(self, entity: EntityData, option: str) -> None:
        """Handles ACTION_CORE_ENTITY_SELECT_OPTION."""
        monitor_id = self._get_monitor_id(entity.id)

        if monitor_id is not None:
            await self.api.async_set_monitor_mode(monitor_id, option)

            await self.async_update_data_providers()

    async def _enable_sound_detection(self, entity: EntityData):
        monitor_id = self._get_monitor_id(entity.id)

        if monitor_id is not None:
            await self.api.async_set_sound_detection(monitor_id, True)

            await self.async_update_data_providers()

    async def _disable_sound_detection(self, entity: EntityData):
        monitor_id = self._get_monitor_id(entity.id)

        if monitor_id is not None:
            await self.api.async_set_sound_detection(monitor_id, False)

            await self.async_update_data_providers()

    async def _enable_motion_detection(self, entity: EntityData):
        monitor_id = self._get_monitor_id(entity.id)

        if monitor_id is not None:
            await self.api.async_set_motion_detection(monitor_id, True)

            await self.async_update_data_providers()

    async def _disable_motion_detection(self, entity: EntityData):
        monitor_id = self._get_monitor_id(entity.id)

        if monitor_id is not None:
            await self.api.async_set_motion_detection(monitor_id, False)

            await self.async_update_data_providers()

    async def _use_original_stream(self, entity: EntityData):
        await self.storage_api.set_use_original_stream(True)

        await self._reload_integration()

    async def _use_default_stream(self, entity: EntityData):
        await self.storage_api.set_use_original_stream(False)

        await self._reload_integration()

    def _get_monitor_id(self, unique_id):
        entity = self.entity_manager.get(unique_id)
        monitor_id = entity.details.get(ATTR_MONITOR_ID)

        return monitor_id

    async def _reload_integration(self):
        data = {ENTITY_CONFIG_ENTRY_ID: self.entry_id}

        await self._hass.services.async_call(HA_NAME, SERVICE_RELOAD_CONFIG_ENTRY, data)
