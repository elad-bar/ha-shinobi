from __future__ import annotations

import logging
from typing import Any

from cryptography.fernet import InvalidToken
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry

from ...core.helpers import get_ha
from ...core.helpers.component_overrides.imports import validate_api_login
from ...core.helpers.const import *
from ...core.models.config_data import (
    ConfigData,
    get_config_data_from_entry,
    get_config_data_from_entry_data,
)
from .password_manager import PasswordManager, async_get_password_manager

_LOGGER = logging.getLogger(__name__)


class ConfigFlowManager:
    _password_manager: PasswordManager
    _config_data: ConfigData | None
    _options: dict | None
    _data: dict | None
    _config_entry: ConfigEntry | None
    title: str

    def __init__(self):
        self._config_entry = None

        self._options = None
        self._data = None

        self._is_initialized = True
        self._hass = None
        self._config_data = None
        self.title = DEFAULT_NAME

    async def initialize(self, hass, config_entry: ConfigEntry | None = None):
        self._config_entry = config_entry
        self._hass = hass
        self._password_manager = await async_get_password_manager(hass)

        data = {}
        options = {}

        if self._config_entry is not None:
            data = self._config_entry.data
            options = self._config_entry.options

            self.title = self._config_entry.title

        await self.update_data(data, CONFIG_FLOW_INIT)
        await self.update_options(options, CONFIG_FLOW_INIT)

    async def update_options(self, options: dict, flow: str):
        _LOGGER.debug(f"Update options for flow '{flow}', Options: {options}")
        validate_login = False

        new_options = self._clone_items(options, flow)

        if flow == CONFIG_FLOW_OPTIONS:
            validate_login = self._should_validate_login(new_options)

            self._move_option_to_data(new_options)

        self._options = new_options

        await self._update_entry()

        if validate_login:
            await self._handle_data(flow)

        return new_options

    async def update_data(self, data: dict, flow: str):
        _LOGGER.debug(f"Update data for flow '{flow}', Data: {data}")

        self._data = self._clone_items(data, flow)

        await self._update_entry()

        await self._handle_data(flow)

        return self._data

    def _get_default_fields(
        self, flow, config_data: ConfigData | None = None
    ) -> dict[vol.Marker, Any]:
        _LOGGER.debug(f"Get default fields for {flow}, Data: {config_data}")

        if config_data is None:
            config_data = self._config_data

        fields = config_data.get_fields()

        return fields

    async def get_default_data(self, user_input) -> vol.Schema:
        _LOGGER.debug(f"Get default data, Input: {user_input}")

        config_data = get_config_data_from_entry_data(user_input, self._password_manager.get)

        fields = self._get_default_fields(CONFIG_FLOW_DATA, config_data)

        data_schema = vol.Schema(fields)

        return data_schema

    def get_default_options(self) -> vol.Schema:
        fields = self._get_default_fields(CONFIG_FLOW_OPTIONS)

        data_schema = vol.Schema(fields)

        return data_schema

    async def _update_entry(self):
        try:
            _LOGGER.debug(f"Update config entry, Data: {self._data}")

            entry = self._get_entry()

            self._config_data = get_config_data_from_entry(entry, self._password_manager.get)

        except InvalidToken:
            _LOGGER.info("Reset password")

            del self._data[CONF_PASSWORD]

            entry = self._get_entry()

            self._config_data = get_config_data_from_entry(entry, self._password_manager.get)

    def _get_entry(self):
        entry = ConfigEntry(version=0,
                            domain="",
                            title="",
                            data=self._data,
                            source="",
                            options=self._options)

        return entry

    def _clone_items(self, user_input, flow: str):
        _LOGGER.debug(f"Clone items for flow '{flow}', Input: {user_input}")

        new_user_input = {}

        if user_input is not None:
            for key in user_input:
                user_input_data = user_input[key]

                new_user_input[key] = user_input_data

            if flow != CONFIG_FLOW_INIT:
                self._password_manager.set(new_user_input)

        return new_user_input

    @staticmethod
    def clone_items(user_input):
        _LOGGER.debug(f"Clone items, Input: {user_input}")

        new_user_input = {}

        if user_input is not None:
            for key in user_input:
                user_input_data = user_input[key]

                new_user_input[key] = user_input_data

        return new_user_input

    def _should_validate_login(self, user_input: dict):
        _LOGGER.debug(f"Checking if validate login is required, user_input: {user_input}")

        should_validate_login = False
        data = self._data

        for conf in CONF_ARR:
            if data.get(conf) != user_input.get(conf):
                should_validate_login = True

                break

        return should_validate_login

    def _get_ha(self, key: str = None):
        if key is None:
            key = self.title

        ha = get_ha(self._hass, key)

        return ha

    def _move_option_to_data(self, options):
        _LOGGER.debug(f"_move_option_to_data, options: {options}")

        for conf in CONF_ARR:
            if conf in options:
                self._data[conf] = options[conf]

                del options[conf]

    async def _handle_data(self, flow):
        _LOGGER.debug(f"_handle_data, flow: {flow}")

        if flow != CONFIG_FLOW_INIT:
            await validate_api_login(self._hass, self._config_data)

        if flow == CONFIG_FLOW_OPTIONS:
            config_entries = self._hass.config_entries
            config_entries.async_update_entry(self._config_entry, data=self._data)
