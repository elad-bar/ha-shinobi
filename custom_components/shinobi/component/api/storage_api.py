"""Storage handlers."""
from __future__ import annotations

import logging
import sys
from typing import Awaitable, Callable

from homeassistant.core import HomeAssistant
from homeassistant.helpers.json import JSONEncoder
from homeassistant.helpers.storage import Store

from ...configuration.models.config_data import ConfigData
from ...core.api.base_api import BaseAPI
from ...core.helpers.enums import ConnectivityStatus
from ..helpers.const import *
from ..models.base_view import ShinobiBaseView

_LOGGER = logging.getLogger(__name__)


class StorageAPI(BaseAPI):
    _stores: dict[str, Store] | None
    _config_data: ConfigData | None
    _data: dict

    def __init__(self,
                 hass: HomeAssistant,
                 async_on_data_changed: Callable[[], Awaitable[None]] | None = None,
                 async_on_status_changed: Callable[[ConnectivityStatus], Awaitable[None]] | None = None
                 ):

        super().__init__(hass, async_on_data_changed, async_on_status_changed)

        self._config_data = None
        self._stores = None
        self._data = {}

    @property
    def _storage_config(self) -> Store:
        storage = self._stores.get(STORAGE_DATA_FILE_CONFIG)

        return storage

    @property
    def use_original_stream(self):
        use_original_stream = self.data.get(STORAGE_DATA_USE_ORIGINAL_STREAM, False)

        return use_original_stream

    async def initialize(self, config_data: ConfigData):
        self._config_data = config_data

        self._initialize_routes()
        self._initialize_storages()

        await self._async_load_configuration()

    def _initialize_storages(self):
        stores = {}

        entry_id = self._config_data.entry.entry_id

        for storage_data_file in STORAGE_DATA_FILES:
            file_name = f"{DOMAIN}.{entry_id}.{storage_data_file}.json"

            stores[storage_data_file] = Store(self.hass, STORAGE_VERSION, file_name, encoder=JSONEncoder)

        self._stores = stores

    def _initialize_routes(self):
        try:
            main_view_data = {}
            entry_id = self._config_data.entry.entry_id

            for key in STORAGE_API_DATA:
                view = ShinobiBaseView(self.hass, key, self._get_data, entry_id)

                main_view_data[key] = view.url

                self.hass.http.register_view(view)

            main_view = self.hass.data.get(MAIN_VIEW)

            if main_view is None:
                main_view = ShinobiBaseView(self.hass, STORAGE_API_LIST, self._get_data)

                self.hass.http.register_view(main_view)
                self.hass.data[MAIN_VIEW] = main_view

            self._data[STORAGE_API_LIST] = main_view_data

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to async_component_initialize, error: {ex}, line: {line_number}")

    async def _async_load_configuration(self):
        """Load the retained data from store and return de-serialized data."""
        self.data = await self._storage_config.async_load()

        if self.data is None:
            self.data = {
                STORAGE_DATA_USE_ORIGINAL_STREAM: False
            }

            await self._async_save()

        _LOGGER.debug(f"Loaded configuration data: {self.data}")

        await self.set_status(ConnectivityStatus.Connected)
        await self.fire_data_changed_event()

    async def _async_save(self):
        """Generate dynamic data to store and save it to the filesystem."""
        _LOGGER.info(f"Save configuration, Data: {self.data}")

        await self._storage_config.async_save(self.data)

        await self.fire_data_changed_event()

    async def set_use_original_stream(self, is_on: bool):
        _LOGGER.debug(f"Set use original stream to {is_on}")

        self.data[STORAGE_DATA_USE_ORIGINAL_STREAM] = is_on

        await self._async_save()

    async def debug_log_api(self, data: dict):
        clean_data = {}
        for key in data:
            if key in [API_DATA_MONITORS]:
                new_monitors = {}
                monitors = data.get(key, {})

                for monitor_key in monitors:
                    monitor = monitors.get(monitor_key)
                    new_monitors[monitor_key] = monitor.to_dict()

                clean_data[key] = new_monitors

            else:
                clean_data[key] = data.get(key)

        self._data[STORAGE_API_DATA_API] = clean_data

    async def debug_log_ws(self, data: dict):
        self._data[STORAGE_API_DATA_WS] = data

    def _get_data(self, key):
        is_list = key == STORAGE_API_LIST

        data = {} if is_list else self._data.get(key)

        if is_list:
            raw_data = self._data.get(key)
            current_entry_id = self._config_data.entry.entry_id

            for entry_id in self.hass.data[DATA].keys():
                entry_data = {}

                for raw_data_key in raw_data:
                    url_raw = raw_data.get(raw_data_key)
                    url = url_raw.replace(current_entry_id, entry_id)

                    entry_data[raw_data_key] = url

                data[entry_id] = entry_data

        return data
