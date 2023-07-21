"""Test."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys

from custom_components.shinobi.common.connectivity_status import ConnectivityStatus
from custom_components.shinobi.managers.rest_api import RestAPI
from custom_components.shinobi.managers.websockets import WebSockets
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PATH,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
)

DATA_KEYS = [CONF_HOST, CONF_PORT, CONF_SSL, CONF_PATH, CONF_USERNAME, CONF_PASSWORD]

DEBUG = str(os.environ.get("DEBUG", False)).lower() == str(True).lower()

log_level = logging.DEBUG if DEBUG else logging.INFO

root = logging.getLogger()
root.setLevel(log_level)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(log_level)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
stream_handler.setFormatter(formatter)
root.addHandler(stream_handler)

_LOGGER = logging.getLogger(__name__)


class Test:
    """Test Class."""

    def __init__(self):
        """Do initialization of test class instance, Returns None."""

        self._api = RestAPI(
            None, None
        )

        self._ws = WebSockets(None, None)

    async def initialize(self):
        """Do initialization of test dependencies instances, Returns None."""

        self.x(1, "2")
        self.x("DSA")

    def x(self, *kwargs):
        print(len(kwargs))

    async def initialize_api(self):

        data = {}

        for key in DATA_KEYS:
            value = os.environ.get(key)

            if value is None:
                raise KeyError(f"Key '{key}' was not set")

            if key == CONF_SSL:
                value = str(value).lower() == str(True).lower()

            data[key] = value

        await self._api.initialize()

    async def terminate(self):
        """Do termination of the API, Return none."""

        await self._api.terminate()

    async def _api_data_changed(self):
        if (
            self._api.status == ConnectivityStatus.Connected
            and self._ws.status == ConnectivityStatus.NotConnected
        ):
            await self._ws.update_api_data(self._api.data)

            await self._ws.initialize(self._config_data)

    async def _api_status_changed(self, status: ConnectivityStatus):
        _LOGGER.info(f"API Status changed to {status.name}")

        if self._api.status == ConnectivityStatus.Connected:
            await self._api.update()

        if self._api.status == ConnectivityStatus.Disconnected:
            await self._ws.terminate()

    async def _ws_data_changed(self):
        data = json.dumps(self._ws.data, indent=4)

        _LOGGER.info(f"WS Data: {data}")

    async def _ws_status_changed(self, status: ConnectivityStatus):
        _LOGGER.info(f"WS Status changed to {status.name}")


instance = Test()
loop = asyncio.new_event_loop()

try:
    loop.run_until_complete(instance.initialize())

except KeyboardInterrupt:
    _LOGGER.info("Aborted")
    loop.run_until_complete(instance.terminate())

except Exception as rex:
    _LOGGER.error(f"Error: {rex}")
