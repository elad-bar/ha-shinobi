from asyncio import sleep
from datetime import datetime
import logging
import sys
from typing import Callable

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import ATTR_ICON, ATTR_STATE
from homeassistant.core import Event
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
    DATA_KEY_PROXY_RECORDINGS,
    DATA_KEY_SOUND,
    DATA_KEY_SOUND_DETECTION,
    DEFAULT_NAME,
    DOMAIN,
    HEARTBEAT_INTERVAL,
    SIGNAL_API_STATUS,
    SIGNAL_MONITOR_ADDED,
    SIGNAL_MONITOR_DISCOVERED,
    SIGNAL_MONITOR_STATUS_CHANGED,
    SIGNAL_MONITOR_TRIGGER,
    SIGNAL_MONITOR_UPDATED,
    SIGNAL_SERVER_ADDED,
    SIGNAL_SERVER_DISCOVERED,
    SIGNAL_WS_STATUS,
    UPDATE_API_INTERVAL,
    UPDATE_ENTITIES_INTERVAL,
    WS_RECONNECT_INTERVAL,
)
from ..common.entity_descriptions import PLATFORMS, IntegrationEntityDescription
from ..common.enums import MonitorMode
from ..models.monitor_data import MonitorData
from ..views import async_setup as views_async_setup
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
            name=config_manager.entry_title,
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
            SIGNAL_MONITOR_STATUS_CHANGED: self._on_monitor_status_changed,
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

    async def on_home_assistant_start(self, _event_data: Event):
        await self.initialize()

    async def initialize(self):
        self._build_data_mapping()

        entry = self.config_manager.entry
        await self.hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        _LOGGER.info(f"Start loading {DOMAIN} integration, Entry ID: {entry.entry_id}")

        views_async_setup(self.hass, self._config_manager)

        await self.async_config_entry_first_refresh()

        await self._api.initialize()

    async def terminate(self):
        await self._websockets.terminate()

    def get_debug_data(self) -> dict:
        config_data = self._config_manager.get_debug_data()

        data = {
            "monitors": self._monitors,
            "config": config_data,
            "api": self._api.data,
            "websockets": self._websockets.data,
        }

        return data

    def get_server_device_info(self) -> DeviceInfo:
        config_data = self.config_manager.config_data
        server_unique_id = slugify(f"{config_data.hostname}_server")
        device_name = f"{self.name} Server"

        device_info = DeviceInfo(
            identifiers={(DOMAIN, server_unique_id)},
            name=device_name,
            model="Server",
            manufacturer=DEFAULT_NAME,
        )

        return device_info

    @staticmethod
    def get_monitor_device_unique_id(monitor: MonitorData):
        unique_id = slugify(f"{monitor.group_id}_{monitor.id}")

        return unique_id

    def get_monitor_device_name(self, monitor: MonitorData):
        device_name = f"{self.name} {monitor.name}"

        return device_name

    def get_monitor(self, monitor_id: str) -> MonitorData:
        monitor = self._monitors.get(monitor_id)

        return monitor

    def get_monitor_device_info(self, monitor_id: str) -> DeviceInfo:
        monitor: MonitorData = self._monitors.get(monitor_id)
        device_name = self.get_monitor_device_name(monitor)

        monitor_unique_id = self.get_monitor_device_unique_id(monitor)

        device_info = DeviceInfo(
            identifiers={(DEFAULT_NAME, monitor_unique_id)},
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
        self, entry_id: str, _group_id, monitor_id, event_type, value
    ):
        if entry_id == self.config_manager.entry_id:
            _LOGGER.debug(
                f"Monitor '{monitor_id}' triggered with event {event_type}: {value}"
            )
            await self.async_request_refresh()

    async def _on_monitor_status_changed(
        self, entry_id: str, monitor_id, status_code: int
    ):
        if entry_id == self.config_manager.entry_id:
            _LOGGER.debug(f"Monitor '{monitor_id}' status changed to {status_code}")
            monitor = self.get_monitor(monitor_id)
            if monitor is not None:
                monitor.status_code = status_code

                self._monitors[monitor.id] = monitor

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
            DATA_KEY_CAMERA: self._get_camera_data,
            DATA_KEY_MONITOR_MODE: self._get_mode_data,
            DATA_KEY_MONITOR_STATUS: self._get_status_data,
            DATA_KEY_MOTION: self._get_motion_status_data,
            DATA_KEY_SOUND: self._get_sound_status_data,
            DATA_KEY_MOTION_DETECTION: self._get_motion_detection_data,
            DATA_KEY_SOUND_DETECTION: self._get_sound_detection_data,
            DATA_KEY_ORIGINAL_STREAM: self._get_original_stream_data,
            DATA_KEY_PROXY_RECORDINGS: self._get_proxy_for_recordings_data,
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
        self,
        entity_description: IntegrationEntityDescription,
        monitor_id: str | None,
        action_key: str,
    ) -> Callable:
        device_data = self.get_data(entity_description, monitor_id)

        actions = device_data.get(ATTR_ACTIONS)
        async_action = actions.get(action_key)

        return async_action

    def _get_camera_data(self, _entity_description, monitor_id: str) -> dict | None:
        monitor = self.get_monitor(monitor_id)

        result = {ATTR_STATE: str(monitor.status_code)}

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
        state = str(monitor.status_code)

        result = {
            ATTR_STATE: state,
        }

        return result

    def _get_motion_status_data(
        self, _entity_description, monitor_id: str
    ) -> dict | None:
        is_on: bool = False

        monitor = self.get_monitor(monitor_id)
        is_online = monitor.is_online

        if is_online:
            is_on = self._websockets.get_trigger_state(
                self._api.group_id, monitor_id, BinarySensorDeviceClass.MOTION
            )

        result = {ATTR_IS_ON: is_on}

        return result

    def _get_sound_status_data(
        self, _entity_description, monitor_id: str
    ) -> dict | None:
        is_on: bool = False

        monitor = self.get_monitor(monitor_id)
        is_online = monitor.is_online

        if is_online:
            is_on = self._websockets.get_trigger_state(
                self._api.group_id, monitor_id, BinarySensorDeviceClass.SOUND
            )

        result = {ATTR_IS_ON: is_on}

        return result

    def _get_motion_detection_data(
        self, _entity_description, monitor_id: str
    ) -> dict | None:
        monitor: MonitorData = self._monitors.get(monitor_id)

        is_on = monitor.is_detector_active(BinarySensorDeviceClass.MOTION)
        icon = monitor.get_detector_icon(BinarySensorDeviceClass.MOTION)

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
        monitor: MonitorData = self._monitors.get(monitor_id)

        is_on = monitor.is_detector_active(BinarySensorDeviceClass.SOUND)
        icon = monitor.get_detector_icon(BinarySensorDeviceClass.SOUND)

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

    def _get_proxy_for_recordings_data(self, _entity_description) -> dict | None:
        is_on = self._config_manager.use_proxy_for_recordings

        result = {
            ATTR_IS_ON: is_on,
            ATTR_ACTIONS: {
                ACTION_ENTITY_TURN_ON: self._set_proxy_for_recordings_enabled,
                ACTION_ENTITY_TURN_OFF: self._set_proxy_for_recordings_disabled,
            },
        }

        return result

    async def _set_monitor_mode(
        self, _entity_description, monitor_id: str, option: str
    ):
        _LOGGER.debug(f"Change monitor {monitor_id} mode, New: {option}")

        await self._api.set_monitor_mode(monitor_id, option)

    async def _set_motion_detection_enabled(self, _entity_description, monitor_id: str):
        _LOGGER.debug(f"Enable monitor {monitor_id} Motion Detection")

        await self._api.set_motion_detection(monitor_id, True)

    async def _set_motion_detection_disabled(
        self, _entity_description, monitor_id: str
    ):
        _LOGGER.debug(f"Disable monitor {monitor_id} Motion Detection")

        await self._api.set_motion_detection(monitor_id, False)

    async def _set_sound_detection_enabled(self, _entity_description, monitor_id: str):
        _LOGGER.debug(f"Enable monitor {monitor_id} Sound Detection")

        await self._api.set_sound_detection(monitor_id, True)

    async def _set_sound_detection_disabled(self, _entity_description, monitor_id: str):
        _LOGGER.debug(f"Disable monitor {monitor_id} Sound Detection")

        await self._api.set_sound_detection(monitor_id, False)

    async def _set_original_stream_enabled(self, _entity_description):
        _LOGGER.debug("Enable Original Stream")

        await self._config_manager.update_original_stream(True)

    async def _set_original_stream_disabled(self, _entity_description):
        _LOGGER.debug("Disable Original Stream")

        await self._config_manager.update_original_stream(False)

    async def _set_proxy_for_recordings_enabled(self, _entity_description):
        _LOGGER.debug("Enable Original Stream")

        await self._config_manager.update_proxy_for_recordings(True)

    async def _set_proxy_for_recordings_disabled(self, _entity_description):
        _LOGGER.debug("Disable Proxy for Recordings")

        await self._config_manager.update_proxy_for_recordings(False)

    @staticmethod
    def _get_date_time_from_timestamp(timestamp):
        result = datetime.fromtimestamp(timestamp)

        return result
