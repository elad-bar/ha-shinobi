"""
This component provides support for Shinobi Video.
For more details about this component, please refer to the documentation at
https://home-assistant.io/components/shinobi/
"""
from __future__ import annotations

import asyncio
from datetime import datetime
import json
import logging
import sys
from typing import Awaitable, Callable

import aiohttp
from aiohttp import ClientSession

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.event import async_track_time_interval

from ...component.helpers.const import *
from ...configuration.models.config_data import ConfigData
from ...core.api.base_api import BaseAPI
from ...core.helpers.enums import ConnectivityStatus

REQUIREMENTS = ["aiohttp"]

_LOGGER = logging.getLogger(__name__)


class IntegrationWS(BaseAPI):
    session: ClientSession | None
    hass: HomeAssistant
    config_data: ConfigData | None
    api_data: dict

    def __init__(self,
                 hass: HomeAssistant,
                 async_on_data_changed: Callable[[], Awaitable[None]] | None = None,
                 async_on_status_changed: Callable[[ConnectivityStatus], Awaitable[None]] | None = None
                 ):

        super().__init__(hass, async_on_data_changed, async_on_status_changed)

        self.config_data = None
        self.session = None
        self.base_url = None
        self.repairing = []
        self._pending_payloads = []
        self._ws = None
        self.api_data = {}
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
        config_data = self.config_data
        protocol = WS_PROTOCOLS[config_data.ssl]

        path = "/" if config_data.path == "" else config_data.path

        url = (
            f"{protocol}://{config_data.host}:{config_data.port}{path}{SHINOBI_WS_ENDPOINT}"
        )

        return url

    @property
    def version(self):
        return self.api_data.get(API_DATA_SOCKET_IO_VERSION, 3)

    @property
    def api_key(self):
        return self.api_data.get(API_DATA_API_KEY)

    @property
    def group_id(self):
        return self.api_data.get(API_DATA_GROUP_ID)

    @property
    def user_id(self):
        return self.api_data.get(API_DATA_USER_ID)

    @property
    def monitors(self):
        return self.api_data.get(API_DATA_MONITORS, {})

    async def update_api_data(self, api_data: dict):
        self.api_data = api_data

    async def initialize(self, config_data: ConfigData):
        _LOGGER.debug(f"Initializing WebSocket.IO v{self.version} connection")

        previous_status = self.status

        try:
            self._remove_async_track_time = async_track_time_interval(
                self.hass, self._check_triggers, TRIGGER_INTERVAL
            )

            self.config_data = config_data

            if self.hass is None:
                if self.session is not None:
                    await self.session.close()

                self.session = aiohttp.client.ClientSession()
            else:
                self.session = async_create_clientsession(hass=self.hass)

        except Exception as ex:
            _LOGGER.warning(f"Failed to create web socket session, Error: {str(ex)}")

        try:
            url = self.ws_url.replace("[VERSION]", str(self.version))

            async with self.session.ws_connect(
                url,
                ssl=False,
                autoclose=True,
                max_msg_size=MAX_MSG_SIZE,
                timeout=SCAN_INTERVAL_WS_TIMEOUT,
            ) as ws:

                await self.set_status(ConnectivityStatus.Connected)

                self._ws = ws

                await self._listen()

        except Exception as ex:
            if self.session is not None and self.session.closed:
                _LOGGER.info(f"WS Session closed")
            else:
                _LOGGER.warning(f"Failed to connect Shinobi Video WS, Error: {ex}")

        if self.status == ConnectivityStatus.Connected:
            await self.set_status(ConnectivityStatus.NotConnected)

            _LOGGER.info("WS Connection terminated")

        else:
            if previous_status == ConnectivityStatus.NotConnected:
                await asyncio.sleep(RECONNECT_INTERVAL)

                await self.fire_status_changed_event()

    async def terminate(self):
        if self._remove_async_track_time is not None:
            self._remove_async_track_time()
            self._remove_async_track_time = None

        await self.set_status(ConnectivityStatus.Disconnected)

        if self._ws is not None:
            await self._ws.close()

            await asyncio.sleep(DISCONNECT_INTERVAL)

        self._ws = None

    async def async_send_heartbeat(self):
        await self._send_ping_message()

    def get_data(self, topic, event_type):
        key = self._get_key(topic, event_type)

        state = self.data.get(key, TRIGGER_DEFAULT)

        return state

    async def _listen(self):
        _LOGGER.info(f"Starting to listen connected")

        async for msg in self._ws:
            continue_to_next = self._handle_next_message(msg)

            if (
                not continue_to_next
                or not self.status == ConnectivityStatus.Connected
            ):
                break

        _LOGGER.info("Stop listening")

    def _handle_next_message(self, msg):
        result = False

        if msg.type in (
            aiohttp.WSMsgType.CLOSE,
            aiohttp.WSMsgType.CLOSED,
            aiohttp.WSMsgType.CLOSING,
        ):
            _LOGGER.info("Connection closed (By Message Close)")

        elif msg.type == aiohttp.WSMsgType.ERROR:
            _LOGGER.warning(f"Connection error, Description: {self._ws.exception()}")

        elif msg.type == aiohttp.WSMsgType.text:
            self.data[API_DATA_LAST_UPDATE] = datetime.now().isoformat()

            result = msg.data is not None and msg.data != "close"

            if result:
                self.hass.async_create_task(self._parse_message(msg.data))

            else:
                _LOGGER.info(f"Message: {msg}")

        else:
            _LOGGER.info(f"Ignoring unsupported message, Type: {msg.type}, Content: {msg}")

        return result

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

    async def _send_ping_message(self):
        _LOGGER.debug("Pinging")

        if self.status == ConnectivityStatus.Connected:
            await self._ws.ping(SHINOBI_WS_PING_MESSAGE)

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

            sensor_type = PLUG_SENSOR_TYPE.get(trigger_reason, None)

            if sensor_type is None:
                event_name = f"{SHINOBI_EVENT}{trigger_reason}"

                _LOGGER.debug(f"Firing event {event_name}, Payload: {payload}")

                self.hass.bus.async_fire(event_name, payload)

            else:
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
                    self.hass.async_create_task(self.fire_data_changed_event())

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to handle sensor message, Error: {ex}, Line: {line_number}")

    def _check_triggers(self, now):
        self.hass.async_create_task(self._async_check_triggers(now))

    async def _async_check_triggers(self, event_time):
        try:
            current_time = datetime.now().timestamp()

            all_keys = self.data.keys()

            changed = False

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
                                changed = True
                                data[TRIGGER_STATE] = STATE_OFF

                                self._set(topic, sensor_type, data)

            if changed:
                await self.fire_data_changed_event()
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
