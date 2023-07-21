from asyncio import sleep
from datetime import datetime
import logging
import sys
from typing import Callable

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import ATTR_ICON, ATTR_STATE, CONF_PASSWORD
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import slugify

from ..common.connectivity_status import ConnectivityStatus
from ..common.consts import (
    ACTION_ENTITY_SELECT_OPTION,
    ACTION_ENTITY_TURN_OFF,
    ACTION_ENTITY_TURN_ON,
    API_RECONNECT_INTERVAL,
    ATTR_ACTIONS,
    ATTR_IS_ON,
    ATTR_MONITOR_GROUP_ID,
    ATTR_MONITOR_ID,
    DATA_KEY_CAMERA,
    DATA_KEY_MONITOR_MODE,
    DATA_KEY_MONITOR_STATUS,
    DATA_KEY_MOTION,
    DATA_KEY_MOTION_DETECTION,
    DATA_KEY_ORIGINAL_STREAM,
    DATA_KEY_SOUND,
    DATA_KEY_SOUND_DETECTION,
    DEFAULT_NAME,
    HEARTBEAT_INTERVAL,
    SIGNAL_API_STATUS,
    SIGNAL_MONITOR_ADDED,
    SIGNAL_MONITOR_DISCOVERED,
    SIGNAL_MONITOR_TRIGGER,
    SIGNAL_MONITOR_UPDATED,
    SIGNAL_SERVER_ADDED,
    SIGNAL_SERVER_DISCOVERED,
    SIGNAL_WS_STATUS,
    UPDATE_API_INTERVAL,
    UPDATE_ENTITIES_INTERVAL,
    WS_RECONNECT_INTERVAL,
)
from ..common.entity_descriptions import IntegrationEntityDescription
from ..common.enums import MonitorMode
from ..common.monitor_data import MonitorData
from .config_manager import ConfigManager
from .rest_api import RestAPI
from .websockets import WebSockets

_LOGGER = logging.getLogger(__name__)


class Coordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    _api: RestAPI
    _websockets: WebSockets | None

    _data_mapping: dict[
        str,
        Callable[[IntegrationEntityDescription], dict | None]
        | Callable[[IntegrationEntityDescription, str], dict | None],
    ] | None
    _system_status_details: dict | None

    _last_update: float
    _last_heartbeat: float
    _monitors = dict[str, MonitorData]

    def __init__(self, hass, config_manager: ConfigManager):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=config_manager.name,
            update_interval=UPDATE_ENTITIES_INTERVAL,
            update_method=self._async_update_data,
        )

        entry = config_manager.entry

        signal_handlers = {
            SIGNAL_API_STATUS: self._on_api_status_changed,
            SIGNAL_WS_STATUS: self._on_ws_status_changed,
            SIGNAL_MONITOR_DISCOVERED: self._on_monitor_discovered,
            SIGNAL_MONITOR_UPDATED: self._on_monitor_updated,
            SIGNAL_MONITOR_TRIGGER: self._on_monitor_triggered,
            SIGNAL_SERVER_DISCOVERED: self._on_server_discovered,
        }

        for signal in signal_handlers:
            handler = signal_handlers[signal]

            entry.async_on_unload(async_dispatcher_connect(hass, signal, handler))

        self._api = RestAPI(hass, config_manager)
        self._websockets = WebSockets(hass, config_manager)

        self._config_manager = config_manager

        self._data_mapping = None

        self._last_update = 0
        self._last_heartbeat = 0
        self._monitors = {}

    @property
    def api(self) -> RestAPI:
        api = self._api

        return api

    @property
    def websockets_data(self) -> dict:
        data = self._websockets.data

        return data

    @property
    def config_manager(self) -> ConfigManager:
        config_manager = self._config_manager

        return config_manager

    async def initialize(self):
        self._build_data_mapping()

        await self._api.initialize()

    def get_device_debug_data(self) -> dict:
        config_data = {}
        for config_item_key in self._config_manager.data:
            if config_item_key not in [CONF_PASSWORD]:
                config_data[config_item_key] = self._config_manager.data[
                    config_item_key
                ]

        data = {
            "config": config_data,
            "api": self._api.data,
            "websockets": self._websockets.data,
        }

        return data

    def get_server_device_info(self) -> DeviceInfo:
        device_name = f"{self._config_manager.name} Server"

        device_info = DeviceInfo(
            identifiers={(DEFAULT_NAME, device_name)},
            name=device_name,
            model="Server",
            manufacturer=DEFAULT_NAME,
        )

        return device_info

    def get_monitor_device_name(self, monitor: MonitorData):
        device_name = f"{self.config_manager.name} {monitor.name}"

        return device_name

    def get_monitor(self, monitor_id: str) -> MonitorData:
        monitor = self._monitors.get(monitor_id)

        return monitor

    def get_monitor_device_info(self, monitor_id: str) -> DeviceInfo:
        monitor = self._monitors.get(monitor_id)
        device_name = self.get_monitor_device_name(monitor)

        device_info = DeviceInfo(
            identifiers={(DEFAULT_NAME, device_name)},
            name=device_name,
            model="Camera",
            manufacturer=DEFAULT_NAME,
        )

        return device_info

    async def get_video_wall(self) -> list[dict] | None:
        if self._api.support_video_browser_api:
            result = self._api.get_video_wall()

        else:
            result = [
                {
                    ATTR_MONITOR_ID: monitor_id,
                    ATTR_MONITOR_GROUP_ID: self._api.group_id,
                }
                for monitor_id in self._monitors
            ]

        return result

    async def _on_api_status_changed(self, entry_id: str, status: ConnectivityStatus):
        if entry_id != self._config_manager.entry_id:
            return

        if status == ConnectivityStatus.Connected:
            await self._api.update()

            await self._websockets.update_api_data(self._api.data)

            await self._websockets.initialize()

        elif status == ConnectivityStatus.Failed:
            await self._websockets.terminate()

            await sleep(API_RECONNECT_INTERVAL.total_seconds())

            await self._api.initialize()

        elif status == ConnectivityStatus.InvalidCredentials:
            self.update_interval = None

    async def _on_ws_status_changed(self, entry_id: str, status: ConnectivityStatus):
        if entry_id != self._config_manager.entry_id:
            return

        if status == ConnectivityStatus.Failed:
            await self._api.initialize()

            await sleep(WS_RECONNECT_INTERVAL.total_seconds())

            await self._api.initialize()

    async def _on_server_discovered(self, entry_id: str):
        if entry_id == self.config_manager.entry_id:
            async_dispatcher_send(
                self.hass, SIGNAL_SERVER_ADDED, self._config_manager.entry_id
            )

    async def _on_monitor_discovered(self, entry_id: str, monitor: MonitorData):
        if entry_id == self.config_manager.entry_id:
            self._monitors[monitor.id] = monitor

            async_dispatcher_send(
                self.hass, SIGNAL_MONITOR_ADDED, self._config_manager.entry_id, monitor
            )

    async def _on_monitor_updated(self, entry_id: str, monitor: MonitorData):
        if entry_id == self.config_manager.entry_id:
            self._monitors[monitor.id] = monitor

    async def _on_monitor_triggered(
        self, entry_id: str, _group_id, _monitor_id, _event_type, _value
    ):
        if entry_id == self.config_manager.entry_id:
            await self.async_request_refresh()

    async def _async_update_data(self):
        """Fetch parameters from API endpoint.

        This is the place to pre-process the parameters to lookup tables
        so entities can quickly look up their parameters.
        """
        try:
            api_connected = self._api.status == ConnectivityStatus.Connected
            aws_client_connected = (
                self._websockets.status == ConnectivityStatus.Connected
            )

            is_ready = api_connected and aws_client_connected

            if is_ready:
                now = datetime.now().timestamp()

                if now - self._last_heartbeat >= HEARTBEAT_INTERVAL.total_seconds():
                    await self._websockets.send_heartbeat()

                    self._last_heartbeat = now

                if now - self._last_update >= UPDATE_API_INTERVAL.total_seconds():
                    await self._api.update()

                    self._last_update = now

            return {}

        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    def _build_data_mapping(self):
        data_mapping = {
            slugify(DATA_KEY_CAMERA): self._get_camera_data,
            slugify(DATA_KEY_MONITOR_MODE): self._get_mode_data,
            slugify(DATA_KEY_MONITOR_STATUS): self._get_status_data,
            slugify(DATA_KEY_MOTION): self._get_motion_status_data,
            slugify(DATA_KEY_SOUND): self._get_sound_status_data,
            slugify(DATA_KEY_MOTION_DETECTION): self._get_motion_detection_data,
            slugify(DATA_KEY_SOUND_DETECTION): self._get_sound_detection_data,
            slugify(DATA_KEY_ORIGINAL_STREAM): self._get_original_stream_data,
        }

        self._data_mapping = data_mapping

        _LOGGER.debug(f"Data retrieval mapping created, Mapping: {self._data_mapping}")

    def get_data(
        self,
        entity_description: IntegrationEntityDescription,
        monitor_id: str | None = None,
    ) -> dict | None:
        result = None

        try:
            handler = self._data_mapping.get(entity_description.key)

            if handler is None:
                _LOGGER.error(
                    f"Handler was not found for {entity_description.key}, Entity Description: {entity_description}"
                )

            else:
                if monitor_id is None:
                    result = handler(entity_description)

                else:
                    result = handler(entity_description, monitor_id)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to extract data for {entity_description}, Error: {ex}, Line: {line_number}"
            )

        return result

    def get_device_action(
        self, entity_description: IntegrationEntityDescription, action_key: str
    ) -> Callable:
        device_data = self.get_data(entity_description)
        actions = device_data.get(ATTR_ACTIONS)
        async_action = actions.get(action_key)

        return async_action

    def _get_camera_data(self, _entity_description, monitor_id: str) -> dict | None:
        monitor = self.get_monitor(monitor_id)

        result = {ATTR_STATE: monitor.status}

        return result

    def _get_mode_data(self, _entity_description, monitor_id: str) -> dict | None:
        monitor = self.get_monitor(monitor_id)
        mode = monitor.mode
        icon = MonitorMode.get_icon(mode)

        result = {
            ATTR_STATE: mode,
            ATTR_ICON: icon,
            ATTR_ACTIONS: {ACTION_ENTITY_SELECT_OPTION: self._set_monitor_mode},
        }

        return result

    def _get_status_data(self, _entity_description, monitor_id: str) -> dict | None:
        monitor = self.get_monitor(monitor_id)
        state = monitor.status

        result = {
            ATTR_STATE: state,
        }

        return result

    def _get_motion_status_data(
        self, _entity_description, monitor_id: str
    ) -> dict | None:
        is_on = self._websockets.get_trigger_state(
            self._api.group_id, monitor_id, BinarySensorDeviceClass.MOTION
        )

        result = {ATTR_IS_ON: is_on}

        return result

    def _get_sound_status_data(
        self, _entity_description, monitor_id: str
    ) -> dict | None:
        is_on = self._websockets.get_trigger_state(
            self._api.group_id, monitor_id, BinarySensorDeviceClass.SOUND
        )

        result = {ATTR_IS_ON: is_on}

        return result

    def _get_motion_detection_data(
        self, _entity_description, monitor_id: str
    ) -> dict | None:
        monitor = self._monitors.get(monitor_id)

        is_on = monitor.has_motion_detector
        icon = "mdi:motion-sensor" if is_on else "mdi:motion-sensor-off"

        result = {
            ATTR_IS_ON: is_on,
            ATTR_ICON: icon,
            ATTR_ACTIONS: {
                ACTION_ENTITY_TURN_ON: self._set_motion_detection_enabled,
                ACTION_ENTITY_TURN_OFF: self._set_motion_detection_disabled,
            },
        }

        return result

    def _get_sound_detection_data(
        self, _entity_description, monitor_id: str
    ) -> dict | None:
        monitor = self._monitors.get(monitor_id)

        is_on = monitor.has_audio_detector
        icon = "mdi:music-note" if is_on else "mdi:music-note-off"

        result = {
            ATTR_IS_ON: is_on,
            ATTR_ICON: icon,
            ATTR_ACTIONS: {
                ACTION_ENTITY_TURN_ON: self._set_sound_detection_enabled,
                ACTION_ENTITY_TURN_OFF: self._set_sound_detection_disabled,
            },
        }

        return result

    def _get_original_stream_data(self, _entity_description) -> dict | None:
        is_on = self._config_manager.use_original_stream

        result = {
            ATTR_IS_ON: is_on,
            ATTR_ACTIONS: {
                ACTION_ENTITY_TURN_ON: self._set_original_stream_enabled,
                ACTION_ENTITY_TURN_OFF: self._set_original_stream_disabled,
            },
        }

        return result

    async def _set_monitor_mode(self, monitor_id: str, option: str):
        _LOGGER.debug(f"Change monitor {monitor_id} mode, New: {option}")

        await self._api.set_monitor_mode(monitor_id, option)

    async def _set_motion_detection_enabled(self, monitor_id: str):
        _LOGGER.debug(f"Enable monitor {monitor_id} Motion Detection")

        await self._api.set_motion_detection(monitor_id, True)

    async def _set_motion_detection_disabled(self, monitor_id: str):
        _LOGGER.debug(f"Disable monitor {monitor_id} Motion Detection")

        await self._api.set_motion_detection(monitor_id, False)

    async def _set_sound_detection_enabled(self, monitor_id: str):
        _LOGGER.debug(f"Enable monitor {monitor_id} Sound Detection")

        await self._api.set_sound_detection(monitor_id, True)

    async def _set_sound_detection_disabled(self, monitor_id: str):
        _LOGGER.debug(f"Disable monitor {monitor_id} Sound Detection")

        await self._api.set_sound_detection(monitor_id, False)

    async def _set_original_stream_enabled(self):
        _LOGGER.debug("Enable Original Stream")

        await self._config_manager.update_original_stream(True)

    async def _set_original_stream_disabled(self):
        _LOGGER.debug("Disable Original Stream")

        await self._config_manager.update_original_stream(False)

    @staticmethod
    def _get_date_time_from_timestamp(timestamp):
        result = datetime.fromtimestamp(timestamp)

        return result
