from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from datetime import datetime
import json
import logging
import sys
from typing import Any, Callable

import aiohttp
from aiohttp import ClientSession

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval

from ..common.connectivity_status import ConnectivityStatus
from ..common.consts import (
    API_DATA_API_KEY,
    API_DATA_GROUP_ID,
    API_DATA_LAST_UPDATE,
    API_DATA_SOCKET_IO_VERSION,
    API_DATA_USER_ID,
    ATTR_EVENT_TYPE,
    ATTR_IS_ON,
    ATTR_MONITOR_GROUP_ID,
    ATTR_MONITOR_ID,
    DISCONNECT_INTERVAL,
    INVALID_JSON_FORMATS,
    MAX_MSG_SIZE,
    PLUG_SENSOR_TYPE,
    SENSOR_AUTO_OFF_INTERVAL,
    SHINOBI_EVENT,
    SHINOBI_WS_ACTION_MESSAGE,
    SHINOBI_WS_CONNECTION_ESTABLISHED_MESSAGE,
    SHINOBI_WS_CONNECTION_READY_MESSAGE,
    SHINOBI_WS_ENDPOINT,
    SHINOBI_WS_PING_MESSAGE,
    SHINOBI_WS_PONG_MESSAGE,
    SIGNAL_MONITOR_STATUS_CHANGED,
    SIGNAL_MONITOR_TRIGGER,
    SIGNAL_WS_READY,
    SIGNAL_WS_STATUS,
    TRIGGER_DEFAULT,
    TRIGGER_DETAILS,
    TRIGGER_DETAILS_PLUG,
    TRIGGER_DETAILS_REASON,
    TRIGGER_INTERVAL,
    TRIGGER_NAME,
    TRIGGER_PLUG,
    TRIGGER_STARTS_WITH,
    TRIGGER_TIMESTAMP,
    URL_PARAMETER_BASE_URL,
    URL_PARAMETER_VERSION,
    WS_CLOSING_MESSAGE,
    WS_COMPRESSION_DEFLATE,
    WS_EVENT_ACTION_PING,
    WS_EVENT_DETECTOR_TRIGGER,
    WS_EVENT_LOG,
    WS_EVENT_MONITOR_STATUS,
    WS_TIMEOUT,
)
from .config_manager import ConfigManager

_LOGGER = logging.getLogger(__name__)


class WebSockets:
    _session: ClientSession | None
    _triggered_sensors: dict
    _api_data: dict
    _config_manager: ConfigManager
    _allowed_handlers: list[str]

    _status: ConnectivityStatus | None
    _on_status_changed: Callable[[ConnectivityStatus], Awaitable[None]]

    def __init__(
        self,
        hass: HomeAssistant | None,
        config_manager: ConfigManager,
    ):
        try:
            self._hass = hass
            self._config_manager = config_manager

            self._status = None
            self._session = None

            self._base_url = None
            self._pending_payloads = []
            self._ws = None
            self._api_data = {}
            self._data = {}
            self._triggered_sensors = {}
            self._remove_async_track_time = None

            self._local_async_dispatcher_send = None

            self._messages_handler: dict = {
                SHINOBI_WS_CONNECTION_ESTABLISHED_MESSAGE: self._handle_connection_established_message,
                SHINOBI_WS_PONG_MESSAGE: self._handle_pong_message,
                SHINOBI_WS_CONNECTION_READY_MESSAGE: self._handle_ready_state_message,
                SHINOBI_WS_ACTION_MESSAGE: self._handle_action_message,
            }

            self._handlers = {
                WS_EVENT_LOG: self._handle_log,
                WS_EVENT_DETECTOR_TRIGGER: self._handle_detector_trigger,
                WS_EVENT_MONITOR_STATUS: self._handle_monitor_status_changed,
            }

            self._allowed_handlers = []

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to load MyDolphin Plus WS, error: {ex}, line: {line_number}"
            )

    @property
    def data(self) -> dict:
        return self._data

    @property
    def status(self) -> str | None:
        status = self._status

        return status

    @property
    def _is_home_assistant(self):
        return self._hass is not None

    @property
    def _has_running_loop(self):
        return self._hass.loop is not None and not self._hass.loop.is_closed()

    @property
    def version(self):
        return self._api_data.get(API_DATA_SOCKET_IO_VERSION, 3)

    @property
    def api_key(self):
        return self._api_data.get(API_DATA_API_KEY)

    @property
    def user_id(self):
        return self._api_data.get(API_DATA_USER_ID)

    @property
    def group_id(self):
        return self._api_data.get(API_DATA_GROUP_ID)

    async def update_api_data(self, api_data: dict):
        self._api_data = api_data

    async def initialize(self):
        try:
            _LOGGER.debug(f"Initializing, Mode: {self._is_home_assistant}")
            self._allowed_handlers = list(self._handlers.keys())

            if self._is_home_assistant:
                self._remove_async_track_time = async_track_time_interval(
                    self._hass, self._check_triggers, TRIGGER_INTERVAL
                )

            else:
                loop = asyncio.get_running_loop()
                loop.call_later(
                    TRIGGER_INTERVAL.total_seconds(), self._check_triggers, None
                )

            await self._initialize_session()

            config_data = self._config_manager.config_data

            data = {
                URL_PARAMETER_BASE_URL: config_data.ws_url,
                URL_PARAMETER_VERSION: self.version,
            }

            url = SHINOBI_WS_ENDPOINT.format(**data)

            async with self._session.ws_connect(
                url,
                ssl=False,
                autoclose=True,
                max_msg_size=MAX_MSG_SIZE,
                timeout=WS_TIMEOUT,
                compress=WS_COMPRESSION_DEFLATE,
            ) as ws:
                self._set_status(ConnectivityStatus.Connected)

                self._ws = ws
                await self._listen()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            if self.status == ConnectivityStatus.Connected:
                _LOGGER.info(
                    f"WS got disconnected will try to recover, Error: {ex}, Line: {line_number}"
                )

                self._set_status(ConnectivityStatus.NotConnected)

            else:
                _LOGGER.warning(
                    f"Failed to connect WS, Error: {ex}, Line: {line_number}"
                )

                self._set_status(ConnectivityStatus.Failed)

    async def terminate(self):
        if self._remove_async_track_time is not None:
            self._remove_async_track_time()
            self._remove_async_track_time = None

        if self._ws is not None:
            await self._ws.close()

            await asyncio.sleep(DISCONNECT_INTERVAL)

        self._set_status(ConnectivityStatus.Disconnected)
        self._ws = None

    async def _initialize_session(self):
        try:
            if self._is_home_assistant:
                self._session = async_create_clientsession(hass=self._hass)

            else:
                self._session = ClientSession()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.warning(
                f"Failed to initialize session, Error: {str(ex)}, Line: {line_number}"
            )

            self._set_status(ConnectivityStatus.Failed)

    async def send_heartbeat(self):
        if self._session is None or self._session.closed:
            self._set_status(ConnectivityStatus.NotConnected)

        if self.status == ConnectivityStatus.Connected:
            try:
                await self._ws.ping(SHINOBI_WS_PING_MESSAGE)

            except ConnectionResetError as crex:
                _LOGGER.debug(
                    f"Gracefully failed to send heartbeat - Restarting connection, Error: {crex}"
                )
                self._set_status(ConnectivityStatus.NotConnected)

            except Exception as ex:
                _LOGGER.error(f"Failed to send heartbeat, Error: {ex}")

    async def _listen(self):
        _LOGGER.info("Starting to listen connected")

        async for msg in self._ws:
            is_ha_running = self._hass.is_running
            is_connected = self.status == ConnectivityStatus.Connected
            is_closing_type = msg.type in WS_CLOSING_MESSAGE
            is_error = msg.type == aiohttp.WSMsgType.ERROR
            can_try_parse_message = msg.type == aiohttp.WSMsgType.TEXT
            is_closing_data = (
                False if is_closing_type or is_error else msg.data == "close"
            )
            session_is_closed = self._session is None or self._session.closed

            not_connected = True in [
                is_closing_type,
                is_error,
                is_closing_data,
                session_is_closed,
                not is_connected,
            ]

            if not is_ha_running:
                self._set_status(ConnectivityStatus.Disconnected)
                return

            elif not_connected:
                _LOGGER.warning(
                    f"WS stopped listening, "
                    f"Message: {str(msg)}, "
                    f"Exception: {self._ws.exception()}"
                )

                self._set_status(ConnectivityStatus.NotConnected)
                return

            elif can_try_parse_message:
                self.data[API_DATA_LAST_UPDATE] = datetime.now().isoformat()

                await self._parse_message(msg.data)

    async def _parse_message(self, message: str):
        try:
            all_keys = self._messages_handler.keys()

            message_handler = None
            current_key = None

            for key in all_keys:
                if f"{key}[" in message or f"{key}{{" in message or key == message:
                    current_key = key
                    message_handler = self._messages_handler.get(current_key)

            if message_handler is None:
                _LOGGER.debug(f"No message handler available, Message: {message}")

            else:
                message_data = message.replace(current_key, "")

                await message_handler(current_key, message_data)

        except Exception as ex:
            _LOGGER.error(
                f"Failed to parse message, Message: {message}, Error: {str(ex)}"
            )

    async def _handle_connection_established_message(self, prefix, data):
        _LOGGER.debug(
            f"WebSocket connection established, ID: {prefix}, Payload: {data}"
        )

        if self.version == 4:
            await self._send(SHINOBI_WS_CONNECTION_READY_MESSAGE)

    @staticmethod
    async def _handle_pong_message(prefix, data):
        _LOGGER.debug(f"Pong message received, ID: {prefix}, Payload: {data}")

    async def _handle_ready_state_message(self, prefix, data):
        _LOGGER.debug(
            f"WebSocket connection state changed to ready, ID: {prefix}, Payload: {data}"
        )

        await self._send_connect_message()

    async def _handle_action_message(self, prefix, data):
        try:
            for bad_format in INVALID_JSON_FORMATS.keys():
                if bad_format in data:
                    fixed_format = INVALID_JSON_FORMATS[bad_format]
                    data = str(data).replace(bad_format, fixed_format)

            payload = json.loads(data)
            action = payload[0]
            data = payload[1]

            if action == "f":
                func = data.get(action)

                if func in self._allowed_handlers:
                    _LOGGER.debug(
                        f"Payload ({prefix}) received, Type: {func}, Data: {data}"
                    )

                    handler: Callable = self._handlers.get(func)

                    if handler is not None:
                        await handler(data)

                elif func != WS_EVENT_LOG:
                    _LOGGER.debug(f"Payload ({prefix}) received, Type: {func}")

            elif action == WS_EVENT_ACTION_PING:
                await self._send_pong_message(data)

            else:
                _LOGGER.debug(
                    f"No payload handler available ({prefix}), Payload: {payload}"
                )

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            supported_event = False
            for key in self._handlers.keys():
                if key in data[0:50]:
                    supported_event = True
                    break

            if supported_event:
                _LOGGER.error(
                    f"Failed to parse message, Data: {data}, Error: {ex}, Line: {line_number}"
                )

            else:
                key = "Unknown"
                unsupported_data = str(data[0:50])

                if unsupported_data.startswith(TRIGGER_STARTS_WITH):
                    key_tmp = unsupported_data.replace(TRIGGER_STARTS_WITH, "")
                    key_arr = key_tmp.split('"')

                    if len(key_arr) > 0:
                        key = key_arr[0]

                _LOGGER.debug(
                    f"Ignoring unsupported event message, Key: {key}, Data: {unsupported_data}"
                )

    async def _handle_log(self, data):
        monitor_id = data.get(ATTR_MONITOR_ID)
        log = data.get("log", {})
        log_type = log.get("type")

        if monitor_id == "$USER" and log_type == "Websocket Connected":
            _LOGGER.debug(log_type)

            if WS_EVENT_LOG in self._allowed_handlers:
                self._allowed_handlers.remove(WS_EVENT_LOG)

            self._async_dispatcher_send(SIGNAL_WS_READY)

    async def _handle_detector_trigger(self, data):
        try:
            _LOGGER.debug(f"Payload received, Data: {data}")

            monitor_id = data.get("id")

            trigger_details = data.get(TRIGGER_DETAILS, {})
            trigger_reason = trigger_details.get(TRIGGER_DETAILS_REASON)

            self.fire_event(trigger_reason, data)

            sensor_type = PLUG_SENSOR_TYPE.get(trigger_reason)

            if sensor_type is not None:
                trigger_name = data.get(TRIGGER_NAME)
                trigger_plug = trigger_details.get(TRIGGER_DETAILS_PLUG)

                if trigger_name is None:
                    trigger_name = trigger_details.get(TRIGGER_NAME)

                event_data = {
                    ATTR_MONITOR_ID: monitor_id,
                    ATTR_EVENT_TYPE: sensor_type,
                    TRIGGER_NAME: trigger_name,
                    TRIGGER_PLUG: trigger_plug,
                    TRIGGER_DETAILS_REASON: trigger_reason,
                    ATTR_IS_ON: True,
                    TRIGGER_TIMESTAMP: datetime.now().timestamp(),
                }

                self._set_trigger_data(monitor_id, sensor_type, event_data)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to handle sensor message, Error: {ex}, Line: {line_number}"
            )

    async def _handle_monitor_status_changed(self, data):
        _LOGGER.debug(f"Monitor status event received, Data: {data}")

        monitor_id = data.get("id")
        status_code = data.get("code")

        self._async_dispatcher_send(
            SIGNAL_MONITOR_STATUS_CHANGED, monitor_id, status_code
        )

    async def _send_connect_message(self):
        message_data = [
            "f",
            {
                "auth": self.api_key,
                "f": "init",
                ATTR_MONITOR_GROUP_ID: self.group_id,
                "uid": self.user_id,
            },
        ]

        json_str = json.dumps(message_data)
        message = f"42{json_str}"

        await self._send(message)

    async def _send_pong_message(self, data):
        message_data = ["pong", data]

        json_str = json.dumps(message_data)
        message = f"42{json_str}"

        await self._send(message)

    async def send_connect_monitor(self, monitor_id: str):
        message_data = [
            "f",
            {
                "auth": self.api_key,
                "f": "monitor",
                "ff": "watch_on",
                "id": monitor_id,
                ATTR_MONITOR_GROUP_ID: self.group_id,
                "uid": self.user_id,
            },
        ]

        json_str = json.dumps(message_data)
        message = f"42{json_str}"

        await self._send(message)

    async def _send(self, message: str):
        _LOGGER.debug(f"Sending message, Data: {message}, Status: {self.status}")

        if self.status == ConnectivityStatus.Connected:
            await self._ws.send_str(message)

    def fire_event(self, trigger: str, data: dict):
        event_name = f"{SHINOBI_EVENT}{trigger}"

        if self._is_home_assistant:
            _LOGGER.debug(f"Firing event {event_name}, Payload: {data}")

            self._hass.bus.async_fire(event_name, data)

        else:
            _LOGGER.info(f"Firing event {event_name}, Payload: {data}")

    def _check_triggers(self, now):
        if self._is_home_assistant:
            self._hass.async_create_task(self._async_check_triggers(now))

        else:
            loop = asyncio.get_running_loop()
            loop.create_task(self._async_check_triggers(datetime.now()))

            loop.call_later(
                TRIGGER_INTERVAL.total_seconds(),
                self._async_check_triggers,
                datetime.now(),
            )

    async def _async_check_triggers(self, event_time):
        try:
            current_time = datetime.now().timestamp()

            keys = [
                key
                for key in self._triggered_sensors
                if self._triggered_sensors.get(key).get(ATTR_IS_ON, False)
            ]

            _LOGGER.debug(f"Checking event's triggers, Identified: {len(keys)}")

            for key in keys:
                event_data = self._triggered_sensors.get(key)

                monitor_id = event_data.get(ATTR_MONITOR_ID)
                event_type = event_data.get(ATTR_EVENT_TYPE)
                trigger_timestamp = event_data.get(TRIGGER_TIMESTAMP)

                diff = current_time - trigger_timestamp
                event_duration = SENSOR_AUTO_OFF_INTERVAL.get(event_type, 20)

                if diff >= event_duration:
                    event_data[ATTR_IS_ON] = False
                    event_data[TRIGGER_TIMESTAMP] = current_time

                    self._set_trigger_data(monitor_id, event_type, event_data)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to check triggers (async) at {event_time}, Error: {ex}, Line: {line_number}"
            )

    @staticmethod
    def _get_trigger_key(monitor_id: str, event_type: str) -> str:
        key = f"{monitor_id}::{event_type}"

        return key

    def _set_trigger_data(self, monitor_id: str, event_type: str, data: dict):
        key = self._get_trigger_key(monitor_id, event_type)

        _LOGGER.debug(f"Set {key}, Data: {data}")

        previous_trigger_state = self.get_trigger_state(monitor_id, event_type)

        self._triggered_sensors[key] = data

        _LOGGER.debug(
            "Update trigger, "
            f"Monitor: {monitor_id}, "
            f"Event: {event_type}, "
            f"Data: {data}"
        )

        current_trigger_state = data.get(ATTR_IS_ON)

        if previous_trigger_state != current_trigger_state:
            self._async_dispatcher_send(
                SIGNAL_MONITOR_TRIGGER,
                monitor_id,
                event_type,
                current_trigger_state,
            )

    def get_trigger_state(self, monitor_id: str, event_type: str) -> bool:
        key = self._get_trigger_key(monitor_id, event_type)

        data = self._triggered_sensors.get(key, TRIGGER_DEFAULT)
        state = data.get(ATTR_IS_ON, False)

        return state

    def _set_status(self, status: ConnectivityStatus):
        if status != self._status:
            log_level = ConnectivityStatus.get_log_level(status)

            _LOGGER.log(
                log_level,
                f"Status changed from '{self._status}' to '{status}'",
            )

            self._status = status

            self._async_dispatcher_send(
                SIGNAL_WS_STATUS,
                status,
            )

    def set_local_async_dispatcher_send(self, callback):
        self._local_async_dispatcher_send = callback

    def _async_dispatcher_send(self, signal: str, *args: Any) -> None:
        if self._hass is None:
            self._local_async_dispatcher_send(
                signal, self._config_manager.entry_id, *args
            )

        else:
            async_dispatcher_send(
                self._hass, signal, self._config_manager.entry_id, *args
            )
