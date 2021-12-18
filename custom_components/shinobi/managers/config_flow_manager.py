import logging
from typing import Any, Dict, Optional

from cryptography.fernet import InvalidToken
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry

from .. import get_ha
from ..api.shinobi_api import ShinobiApi
from ..helpers.const import *
from ..managers.configuration_manager import ConfigManager
from ..managers.password_manager import PasswordManager
from ..models import LoginError
from ..models.config_data import ConfigData

_LOGGER = logging.getLogger(__name__)


class ConfigFlowManager:
    _config_manager: ConfigManager
    _password_manager: PasswordManager
    _options: Optional[dict]
    _data: Optional[dict]
    _config_entry: Optional[ConfigEntry]
    api: Optional[ShinobiApi]
    title: str

    def __init__(self):
        self._config_entry = None

        self._options = None
        self._data = None

        self._is_initialized = True
        self._hass = None
        self.api = None
        self.title = DEFAULT_NAME

    async def initialize(self, hass, config_entry: Optional[ConfigEntry] = None):
        self._config_entry = config_entry
        self._hass = hass

        self._password_manager = PasswordManager(self._hass)
        self._config_manager = ConfigManager(self._password_manager)

        data = {}
        options = {}

        if self._config_entry is not None:
            data = self._config_entry.data
            options = self._config_entry.options

            self.title = self._config_entry.title

        await self.update_data(data, CONFIG_FLOW_INIT)
        await self.update_options(options, CONFIG_FLOW_INIT)

    @property
    def config_data(self) -> ConfigData:
        return self._config_manager.data

    async def update_options(self, options: dict, flow: str):
        _LOGGER.debug(f"update_options, options: {options}, flow: {flow}")
        validate_login = False

        new_options = await self._clone_items(options, flow)

        if flow == CONFIG_FLOW_OPTIONS:
            validate_login = self._should_validate_login(new_options)

            self._move_option_to_data(new_options)

        self._options = new_options

        await self._update_entry()

        if validate_login:
            await self._handle_data(flow)

        return new_options

    async def update_data(self, data: dict, flow: str):
        _LOGGER.debug(f"update_data, data: {data}, flow: {flow}")

        self._data = await self._clone_items(data, flow)

        await self._update_entry()

        await self._handle_data(flow)

        return self._data

    def _get_default_fields(
        self, flow, config_data: Optional[ConfigData] = None
    ) -> Dict[vol.Marker, Any]:
        _LOGGER.debug(f"Get default fields for {flow}, config_data: {config_data}")

        if config_data is None:
            config_data = self.config_data

        fields = {
            vol.Optional(CONF_HOST, default=config_data.host): str,
            vol.Optional(CONF_PATH, default=config_data.path): str,
            vol.Optional(CONF_PORT, default=config_data.port): int,
            vol.Optional(CONF_SSL, default=config_data.ssl): bool,
            vol.Optional(CONF_USERNAME, default=config_data.username): str,
            vol.Optional(CONF_PASSWORD, default=config_data.password_clear_text): str,
            vol.Optional(CONF_USE_ORIGINAL_STREAM, default=config_data.use_original_stream): bool,
        }

        return fields

    async def get_default_data(self, user_input) -> vol.Schema:
        _LOGGER.debug(f"Get default data, user_input: {user_input}")

        config_data = await self._config_manager.get_basic_data(user_input)

        fields = self._get_default_fields(CONFIG_FLOW_DATA, config_data)

        data_schema = vol.Schema(fields)

        return data_schema

    def get_default_options(self) -> vol.Schema:
        fields = self._get_default_fields(CONFIG_FLOW_OPTIONS)

        data_schema = vol.Schema(fields)

        return data_schema

    async def _update_entry(self):
        try:
            _LOGGER.debug(f"_update_entry, data: {self._data}")

            entry = ConfigEntry(version=0,
                                domain="",
                                title="",
                                data=self._data,
                                source="",
                                options=self._options)

            await self._config_manager.update(entry)
        except InvalidToken:
            _LOGGER.info("Reset password")

            del self._data[CONF_PASSWORD]

            entry = ConfigEntry(version=0,
                                domain="",
                                title="",
                                data=self._data,
                                source="",
                                options=self._options)

            await self._config_manager.update(entry)

    async def _handle_password(self, user_input):
        _LOGGER.debug(f"_handle_password, user_input: {user_input}")

        if CONF_PASSWORD in user_input:
            password_clear_text = user_input[CONF_PASSWORD]
            password = await self._password_manager.encrypt(password_clear_text)

            user_input[CONF_PASSWORD] = password

    async def _clone_items(self, user_input, flow: str):
        _LOGGER.debug(f"_clone_items, user_input: {user_input}, flow: {flow}")

        new_user_input = {}

        if user_input is not None:
            for key in user_input:
                user_input_data = user_input[key]

                new_user_input[key] = user_input_data

            if flow != CONFIG_FLOW_INIT:
                await self._handle_password(new_user_input)

        return new_user_input

    @staticmethod
    def clone_items(user_input):
        _LOGGER.debug(f"clone_items, user_input: {user_input}")

        new_user_input = {}

        if user_input is not None:
            for key in user_input:
                user_input_data = user_input[key]

                new_user_input[key] = user_input_data

        return new_user_input

    def _should_validate_login(self, user_input: dict):
        _LOGGER.debug(f"_should_validate_login, user_input: {user_input}")

        validate_login = False
        data = self._data

        for conf in CONF_ARR:
            if data.get(conf) != user_input.get(conf):
                validate_login = True

                break

        return validate_login

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
            await self._valid_login()

        if flow == CONFIG_FLOW_OPTIONS:
            config_entries = self._hass.config_entries
            config_entries.async_update_entry(self._config_entry, data=self._data)

    async def _valid_login(self):
        _LOGGER.debug(f"_valid_login")

        errors = None

        config_data = self._config_manager.data

        api = ShinobiApi(self._hass, self._config_manager)
        await api.initialize()

        is_logged_in = await api.login()

        if not is_logged_in:
            _LOGGER.warning(f"Failed to access Shinobi Video server ({config_data.host})")
            errors = {"base": "invalid_server_details"}

        if errors is not None:
            raise LoginError(errors)
