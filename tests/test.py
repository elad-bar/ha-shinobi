"""Test."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys

from custom_components.shinobi.component.api.api import IntegrationAPI
from custom_components.shinobi.component.api.websocket import IntegrationWS
from custom_components.shinobi.component.helpers.const import *
from custom_components.shinobi.configuration.models.config_data import ConfigData
from custom_components.shinobi.core.helpers.enums import ConnectivityStatus

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

        self._api = IntegrationAPI(
            None, self._api_data_changed, self._api_status_changed
        )

        self._ws = IntegrationWS(None, self._ws_data_changed, self._ws_status_changed)

        self._config_data: ConfigData | None = None

    async def initialize(self):
        """Do initialization of test dependencies instances, Returns None."""

        data = {}

        for key in DATA_KEYS:
            value = os.environ.get(key)

            if value is None:
                raise KeyError(f"Key '{key}' was not set")

            if key == CONF_SSL:
                value = str(value).lower() == str(True).lower()

            data[key] = value

        self._config_data = ConfigData.from_dict(data)

        await self._api.initialize(self._config_data)

    async def terminate(self):
        """Do termination of the API, Return none."""

        await self._api.terminate()

    async def _api_data_changed(self):
        data = self._get_api_data()

        _LOGGER.info(f"API Data: {data}")

        if (
            self._api.status == ConnectivityStatus.Connected
            and self._ws.status == ConnectivityStatus.NotConnected
        ):
            await self._ws.update_api_data(self._api.data)

            await self._ws.initialize(self._config_data)

    async def _api_status_changed(self, status: ConnectivityStatus):
        _LOGGER.info(f"API Status changed to {status.name}")

        if self._api.status == ConnectivityStatus.Connected:
            await self._api.async_update()

        if self._api.status == ConnectivityStatus.Disconnected:
            await self._ws.terminate()

    async def _ws_data_changed(self):
        data = json.dumps(self._ws.data, indent=4)

        _LOGGER.info(f"WS Data: {data}")

    async def _ws_status_changed(self, status: ConnectivityStatus):
        _LOGGER.info(f"WS Status changed to {status.name}")

    def _get_api_data(self) -> str:
        data = self._api.data
        clean_data = {}

        try:
            for key in data:
                if key in [API_DATA_MONITORS]:
                    new_monitors = {}
                    monitors = data.get(key, {})

                    for monitor_key in monitors:
                        monitor = monitors.get(monitor_key)
                        new_monitors[monitor_key] = monitor.to_dict()

                    clean_data[key] = new_monitors
                elif key in [API_DATA_LAST_UPDATE]:
                    clean_data[key] = str(data.get(key))

                else:
                    clean_data[key] = data.get(key)
        except Exception as ex:
            _LOGGER.error(f"Failed to get API data, Data: {data} Error: {ex}")

        result = json.dumps(clean_data, indent=4)

        return result


instance = Test()
loop = asyncio.new_event_loop()

try:
    loop.run_until_complete(instance.initialize())

except KeyboardInterrupt:
    _LOGGER.info("Aborted")
    loop.run_until_complete(instance.terminate())

except Exception as rex:
    _LOGGER.error(f"Error: {rex}")
