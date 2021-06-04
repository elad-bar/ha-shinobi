"""
This component provides support for Shinobi Video.
For more details about this component, please refer to the documentation at
https://home-assistant.io/components/shinobi/
"""
import asyncio
from datetime import datetime
import json
import logging
from typing import Callable, Optional

import aiohttp
from aiohttp import ClientSession

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from ..helpers.const import *
from ..managers.configuration_manager import ConfigManager
from ..managers.event_manager import EventManager
from ..models.camera_data import CameraData
from ..models.config_data import ConfigData
from .shinobi_api import ShinobiApi

REQUIREMENTS = ["aiohttp"]

_LOGGER = logging.getLogger(__name__)


class ShinobiWebSocket:
    is_connected: bool
    api: ShinobiApi
    session: Optional[ClientSession]
    hass: HomeAssistant
    config_manager: ConfigManager
    event_manager: EventManager
    base_url: Optional[str]
    is_aborted: bool

    def __init__(self,
                 hass: HomeAssistant,
                 api: ShinobiApi,
                 config_manager: ConfigManager,
                 event_manager: EventManager):

        self.config_manager = config_manager
        self._last_update = datetime.now()
        self.event_manager = event_manager
        self.hass = hass
        self._session = None
        self._ws = None
        self._pending_payloads = []
        self.is_connected = False
        self.api = api
        self.is_aborted = False

        self._handlers = {
            "log": self.handle_log,
            "detector_trigger": self.handle_detector_trigger
        }

    @property
    def config_data(self) -> Optional[ConfigData]:
        if self.config_manager is not None:
            return self.config_manager.data

        return None

    async def initialize(self):
        _LOGGER.debug("Initializing WS connection")

        try:
            cd = self.config_data

            self.base_url = (
                f"{cd.ws_protocol}://{cd.host}:{cd.port}{cd.path}{SHINOBI_WS_ENDPOINT}"
            )

            if self.is_connected:
                await self.close()

            if self.hass is None:
                self._session = aiohttp.client.ClientSession()
            else:
                self._session = async_create_clientsession(hass=self.hass)

        except Exception as ex:
            _LOGGER.warning(f"Failed to create session of EdgeOS WS, Error: {str(ex)}")

        try:
            async with self._session.ws_connect(
                self.base_url,
                ssl=False,
                autoclose=True,
                max_msg_size=MAX_MSG_SIZE,
                timeout=SCAN_INTERVAL_WS_TIMEOUT,
            ) as ws:

                self.is_connected = True

                self._ws = ws

                await self.listen()

        except Exception as ex:
            if self._session is not None and self._session.closed:
                _LOGGER.info(f"WS Session closed")
            else:
                _LOGGER.warning(f"Failed to connect Shinobi Video WS, Error: {ex}")

        self.is_connected = False

        _LOGGER.info("WS Connection terminated")

    @property
    def is_initialized(self):
        is_initialized = self._session is not None and not self._session.closed

        return is_initialized

    @property
    def last_update(self):
        result = self._last_update

        return result

    async def async_send_heartbeat(self, timestamp):
        await self.send_ping_message()

    async def listen(self):
        _LOGGER.info(f"Starting to listen connected")

        async for msg in self._ws:
            continue_to_next = self.handle_next_message(msg)

            if (
                not continue_to_next
                or not self.is_initialized
                or not self.is_connected
            ):
                break

        _LOGGER.info(f"Stop listening")

    def handle_next_message(self, msg):
        result = False

        if msg.type in (
            aiohttp.WSMsgType.CLOSE,
            aiohttp.WSMsgType.CLOSED,
            aiohttp.WSMsgType.CLOSING,
        ):
            _LOGGER.info("Connection closed (By Message Close)")

        elif msg.type == aiohttp.WSMsgType.ERROR:
            _LOGGER.warning(f"Connection error, Description: {self._ws.exception()}")

        else:
            self._last_update = datetime.now()

            if msg.data == "close":
                result = False
            else:
                self.hass.async_create_task(self.parse_message(msg.data))
                result = True

        return result

    async def parse_message(self, message: str):
        if message.startswith(SHINOBI_WS_CONNECTION_ESTABLISHED_MESSAGE):
            _LOGGER.debug(f"Connected, Message: {message[1:]}")

        elif message.startswith(SHINOBI_WS_PONG_MESSAGE):
            _LOGGER.debug(f"Pong received")

        elif message.startswith(SHINOBI_WS_CONNECTION_READY_MESSAGE):
            _LOGGER.debug(f"Back channel connected")
            await self.send_connect_message()

        elif message.startswith(SHINOBI_WS_ACTION_MESSAGE):
            json_str = message[2:]
            payload = json.loads(json_str)
            await self.parse_payload(payload)

        else:
            _LOGGER.debug(f"No message handler available, Message: {message}")

    async def parse_payload(self, payload):
        action = payload[0]
        data = payload[1]

        if action == "f":
            func = data.get(action)

            if func in self._handlers.keys():
                handler: Callable = self._handlers.get(func, None)

                if handler is not None:
                    await handler(data)

            else:
                _LOGGER.debug(f"Payload received, Type: {func}")

        else:
            _LOGGER.debug(f"No payload handler available, Payload: {payload}")

    async def handle_log(self, data):
        monitor_id = data.get("mid")
        log = data.get("log", {})
        log_type = log.get("type")

        if monitor_id == "$USER" and log_type == "Websocket Connected":
            _LOGGER.debug(f"WebSocket Connected")

            monitors = self.api.camera_list

            for monitor in monitors:
                await self.send_connect_monitor(monitor)

    async def handle_detector_trigger(self, data):
        _LOGGER.debug(f"Payload received, Data: {data}")

        monitor_id = data.get("id")
        group_id = data.get("ke")

        topic = f"{group_id}/{monitor_id}"

        self.event_manager.message_received(topic, data)

    async def send_connect_message(self):
        message_data = [
            "f",
            {
                "auth": self.api.api_key,
                "f": "init",
                "ke": self.api.group_id,
                "uid": self.api.user_id
            }
        ]

        json_str = json.dumps(message_data)
        message = f"42{json_str}"

        await self.send(message)

    async def send_ping_message(self):
        _LOGGER.debug("Pinging")

        await self.send(SHINOBI_WS_PING_MESSAGE)

    async def send_connect_monitor(self, monitor: CameraData):
        message_data = [
            "f",
            {
                "auth": self.api.api_key,
                "f": "monitor",
                "ff": "watch_on",
                "id": monitor.monitorId,
                "ke": self.api.group_id,
                "uid": self.api.user_id
            }
        ]

        json_str = json.dumps(message_data)
        message = f"42{json_str}"

        await self.send(message)

    async def send(self, message: str):
        _LOGGER.debug(f"Sending message, Data: {message}, Connected: {self.is_connected}")

        if self.is_connected:
            await self._ws.send_str(message)

    async def terminate(self):
        self.is_aborted = True

        await self.close()

    async def close(self):
        _LOGGER.info("Closing connection to WS")

        self.is_connected = False

        if self._ws is not None:
            await self._ws.close()

            await asyncio.sleep(DISCONNECT_INTERVAL)

        self._ws = None
