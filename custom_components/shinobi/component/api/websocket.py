"""
This component provides support for Shinobi Video.
For more details about this component, please refer to the documentation at
https://home-assistant.io/components/shinobi/
"""
from __future__ import annotations

import asyncio
from asyncio import sleep
from collections.abc import Awaitable, Callable
from datetime import datetime
import json
import logging
import sys

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from ...component.helpers.const import *
from ...configuration.models.config_data import ConfigData
from ...core.api.base_api import BaseAPI
from ...core.helpers.enums import ConnectivityStatus

_LOGGER = logging.getLogger(__name__)


class IntegrationWS(BaseAPI):
    _config_data: ConfigData | None
    _api_data: dict

    def __init__(self,
                 hass: HomeAssistant | None,
                 async_on_data_changed: Callable[[], Awaitable[None]] | None = None,
                 async_on_status_changed: Callable[[ConnectivityStatus], Awaitable[None]] | None = None
                 ):

        super().__init__(hass, async_on_data_changed, async_on_status_changed)

        self._config_data = None
        self._base_url = None
        self._repairing = []
        self._pending_payloads = []
        self._ws = None
        self._api_data = {}
        self._remove_async_track_time = None

        self._messages_handler: dict = {
            SHINOBI_WS_CONNECTION_ESTABLISHED_MESSAGE: self._handle_connection_established_message,
            SHINOBI_WS_PONG_MESSAGE: self._handle_pong_message,
            SHINOBI_WS_CONNECTION_READY_MESSAGE: self._handle_ready_state_message,
            SHINOBI_WS_ACTION_MESSAGE: self._handle_action_message
        }

        self._handlers = {
            "log": self._handle_log,
            "detector_trigger": self._handle_detector_trigger
        }

    @property
    def ws_url(self):
        config_data = self._config_data
        protocol = WS_PROTOCOLS[config_data.ssl]

        path = "/" if config_data.path == "" else config_data.path

        url = (
            f"{protocol}://{config_data.host}:{config_data.port}{path}"
        )

        return url

    @property
    def version(self):
        return self._api_data.get(API_DATA_SOCKET_IO_VERSION, 3)

    @property
    def api_key(self):
        return self._api_data.get(API_DATA_API_KEY)

    @property
    def group_id(self):
        return self._api_data.get(API_DATA_GROUP_ID)

    @property
    def user_id(self):
        return self._api_data.get(API_DATA_USER_ID)

    @property
    def monitors(self):
        return self._api_data.get(API_DATA_MONITORS, {})

    async def update_api_data(self, api_data: dict):
        self._api_data = api_data

    async def initialize(self, config_data: ConfigData | None = None):
        if config_data is None:
            _LOGGER.debug(f"Reinitializing WebSocket connection")

        else:
            self._config_data = config_data

            _LOGGER.debug(f"Initializing WebSocket connection")

        try:
            if self.is_home_assistant:
                self._remove_async_track_time = async_track_time_interval(
                    self.hass, self._check_triggers, TRIGGER_INTERVAL
                )

            else:
                loop = asyncio.get_running_loop()
                loop.call_later(TRIGGER_INTERVAL.total_seconds(), self._check_triggers, None)

            await self.initialize_session()

            data = {
                URL_PARAMETER_BASE_URL: self.ws_url,
                URL_PARAMETER_VERSION: self.version
            }

            url = SHINOBI_WS_ENDPOINT.format(**data)

            async with self.session.ws_connect(
                url,
                ssl=False,
                autoclose=True,
                max_msg_size=MAX_MSG_SIZE,
                timeout=WS_TIMEOUT,
                compress=WS_COMPRESSION_DEFLATE
            ) as ws:

                await self.set_status(ConnectivityStatus.Connected)

                self._ws = ws

                await self._listen()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            if self.status == ConnectivityStatus.Connected:
                _LOGGER.info(f"WS got disconnected will try to recover, Error: {ex}, Line: {line_number}")

                await self.set_status(ConnectivityStatus.NotConnected)

            else:
                _LOGGER.warning(f"Failed to connect WS, Error: {ex}, Line: {line_number}")

                await self.set_status(ConnectivityStatus.Failed)

    async def terminate(self):
        await super().terminate()

        if self._remove_async_track_time is not None:
            self._remove_async_track_time()
            self._remove_async_track_time = None

        if self._ws is not None:
            await self._ws.close()

            await asyncio.sleep(DISCONNECT_INTERVAL)

        self._ws = None

    async def async_send_heartbeat(self):
        if self.session is None or self.session.closed:
            await self.set_status(ConnectivityStatus.NotConnected)

        if self.status == ConnectivityStatus.Connected:
            await self._ws.ping(SHINOBI_WS_PING_MESSAGE)

    def get_data(self, topic, event_type):
        key = self._get_key(topic, event_type)

        state = self.data.get(key, TRIGGER_DEFAULT)

        return state

    async def _listen(self):
        _LOGGER.info(f"Starting to listen connected")

        listening = True

        while listening and self.status == ConnectivityStatus.Connected:
            async for msg in self._ws:
                is_connected = self.status == ConnectivityStatus.Connected
                is_closing_type = msg.type in WS_CLOSING_MESSAGE
                is_error = msg.type == aiohttp.WSMsgType.ERROR
                can_try_parse_message = msg.type == aiohttp.WSMsgType.TEXT
                is_closing_data = False if is_closing_type or is_error else msg.data == "close"
                session_is_closed = self.session is None or self.session.closed

                if is_closing_type or is_error or is_closing_data or session_is_closed or not is_connected:
                    _LOGGER.warning(
                        f"WS stopped listening, "
                        f"Message: {str(msg)}, "
                        f"Exception: {self._ws.exception()}"
                    )

                    if is_connected:
                        await self.set_status(ConnectivityStatus.NotConnected)

                    listening = False
                    break

                elif can_try_parse_message:
                    self.data[API_DATA_LAST_UPDATE] = datetime.now().isoformat()

                    await self._parse_message(msg.data)

            _LOGGER.info("Message queue is empty, will try to resample in a second")

            await sleep(1)

        _LOGGER.info(f"Stop listening")

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
            _LOGGER.error(f"Failed to parse message, Message: {message}, Error: {str(ex)}")

    async def _handle_connection_established_message(self, prefix, data):
        _LOGGER.debug(f"WebSocket connection established, ID: {prefix}, Payload: {data}")

        if self.version == 4:
            await self._send(SHINOBI_WS_CONNECTION_READY_MESSAGE)

    @staticmethod
    async def _handle_pong_message(prefix, data):
        _LOGGER.debug(f"Pong message received, ID: {prefix}, Payload: {data}")

    async def _handle_ready_state_message(self, prefix, data):
        _LOGGER.debug(f"WebSocket connection state changed to ready, ID: {prefix}, Payload: {data}")

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

                if func in self._handlers.keys():
                    handler: Callable = self._handlers.get(func, None)

                    if handler is not None:
                        await handler(data)

                else:
                    _LOGGER.debug(f"Payload ({prefix}) received, Type: {func}")

            elif action == "ping":
                await self._send_pong_message(data)

            else:
                _LOGGER.debug(f"No payload handler available ({prefix}), Payload: {payload}")

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            supported_event = False
            for key in self._handlers.keys():
                if key in data[0:50]:
                    supported_event = True
                    break

            if supported_event:
                _LOGGER.error(f"Failed to parse message, Data: {data}, Error: {ex}, Line: {line_number}")

            else:
                key = "Unknown"
                unsupported_data = str(data[0:50])

                if unsupported_data.startswith(TRIGGER_STARTS_WITH):
                    key_tmp = unsupported_data.replace(TRIGGER_STARTS_WITH, "")
                    key_arr = key_tmp.split("\"")

                    if len(key_arr) > 0:
                        key = key_arr[0]

                _LOGGER.debug(f"Ignoring unsupported event message, Key: {key}, Data: {unsupported_data}")

    async def _handle_log(self, data):
        monitor_id = data.get(ATTR_MONITOR_ID)
        log = data.get("log", {})
        log_type = log.get("type")

        if monitor_id == "$USER" and log_type == "Websocket Connected":
            _LOGGER.debug(f"WebSocket Connected")

            for monitor_id in self.monitors:
                await self._send_connect_monitor(monitor_id)

    async def _handle_detector_trigger(self, data):
        _LOGGER.debug(f"Payload received, Data: {data}")

        monitor_id = data.get("id")
        group_id = data.get(ATTR_MONITOR_GROUP_ID)

        topic = f"{group_id}/{monitor_id}"

        self._message_received(topic, data)

    async def _send_connect_message(self):
        message_data = [
            "f",
            {
                "auth": self.api_key,
                "f": "init",
                ATTR_MONITOR_GROUP_ID: self.group_id,
                "uid": self.user_id
            }
        ]

        json_str = json.dumps(message_data)
        message = f"42{json_str}"

        await self._send(message)

    async def _send_pong_message(self, data):
        message_data = [
            "pong", data
        ]

        json_str = json.dumps(message_data)
        message = f"42{json_str}"

        await self._send(message)

    async def _send_connect_monitor(self, monitor_id: str):
        message_data = [
            "f",
            {
                "auth": self.api_key,
                "f": "monitor",
                "ff": "watch_on",
                "id": monitor_id,
                ATTR_MONITOR_GROUP_ID: self.group_id,
                "uid": self.user_id
            }
        ]

        json_str = json.dumps(message_data)
        message = f"42{json_str}"

        await self._send(message)

    async def _send(self, message: str):
        _LOGGER.debug(f"Sending message, Data: {message}, Status: {self.status}")

        if self.status == ConnectivityStatus.Connected:
            await self._ws.send_str(message)

    def _message_received(self, topic, payload):
        try:
            trigger_details = payload.get(TRIGGER_DETAILS, {})
            trigger_reason = trigger_details.get(TRIGGER_DETAILS_REASON)

            self.fire_event(trigger_reason, payload)

            sensor_type = PLUG_SENSOR_TYPE.get(trigger_reason, None)

            if sensor_type is not None:
                trigger_name = payload.get(TRIGGER_NAME)
                trigger_plug = trigger_details.get(TRIGGER_DETAILS_PLUG)

                if trigger_name is None:
                    trigger_name = trigger_details.get(TRIGGER_NAME)

                value = {
                    TRIGGER_NAME: trigger_name,
                    TRIGGER_PLUG: trigger_plug,
                    TRIGGER_DETAILS_REASON: trigger_reason,
                    TRIGGER_STATE: STATE_ON,
                    TRIGGER_TIMESTAMP: datetime.now().timestamp(),
                    TRIGGER_TOPIC: topic
                }

                previous_data = self.get_data(topic, sensor_type)
                previous_state = previous_data.get(TRIGGER_STATE, STATE_OFF)

                self._set(topic, sensor_type, value)

                if previous_state == STATE_OFF:
                    if self.is_home_assistant:
                        self.hass.async_create_task(self.fire_data_changed_event())

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to handle sensor message, Error: {ex}, Line: {line_number}")

    def fire_event(self, trigger: str, data: dict):
        event_name = f"{SHINOBI_EVENT}{trigger}"

        if self.is_home_assistant:
            _LOGGER.debug(f"Firing event {event_name}, Payload: {data}")

            self.hass.bus.async_fire(event_name, data)

        else:
            _LOGGER.info(f"Firing event {event_name}, Payload: {data}")

    def _check_triggers(self, now):
        if self.is_home_assistant:
            self.hass.async_create_task(self._async_check_triggers(now))

        else:
            loop = asyncio.get_running_loop()
            loop.create_task(self._async_check_triggers(datetime.now()))

            loop.call_later(TRIGGER_INTERVAL.total_seconds(), self._check_triggers, datetime.now())

    async def _async_check_triggers(self, event_time):
        try:
            current_time = datetime.now().timestamp()

            all_keys = self.data.keys()

            changes = []

            for key in all_keys:
                if key != API_DATA_LAST_UPDATE:
                    data = self.data.get(key)

                    if data is not None:
                        topic = data.get(TRIGGER_TOPIC, None)
                        trigger_reason = data.get(TRIGGER_DETAILS_REASON, None)
                        trigger_timestamp = data.get(TRIGGER_TIMESTAMP, None)
                        trigger_state = data.get(TRIGGER_STATE, STATE_OFF)

                        if topic is not None and trigger_state == STATE_ON:
                            sensor_type = PLUG_SENSOR_TYPE[trigger_reason]

                            diff = current_time - trigger_timestamp
                            event_duration = SENSOR_AUTO_OFF_INTERVAL.get(sensor_type, 20)

                            if diff >= event_duration:
                                data[TRIGGER_STATE] = STATE_OFF

                                self._set(topic, sensor_type, data)

                                changes.append(f"{topic} {sensor_type}")

            if len(changes) > 0:
                if self.is_home_assistant:
                    await self.fire_data_changed_event()

                else:
                    message = ", ".join(changes)

                    _LOGGER.info(f"Manual events: {message}")

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to check triggers (async) at {event_time}, Error: {ex}, Line: {line_number}"
            )

    def _set(self, topic, event_type, value):
        _LOGGER.debug(f"Set {event_type} state: {value} for {topic}")

        key = self._get_key(topic, event_type)

        self.data[key] = value

    @staticmethod
    def _get_key(topic, event_type):
        key = f"{topic}_{event_type}".lower()

        return key
