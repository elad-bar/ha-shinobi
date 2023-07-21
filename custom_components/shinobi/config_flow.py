"""Config flow to configure."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PATH,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
)

from . import LoginError
from .common.connectivity_status import ConnectivityStatus
from .common.consts import DEFAULT_NAME, DEFAULT_PORT, DOMAIN
from .managers.config_manager import ConfigManager
from .managers.rest_api import RestAPI

_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class DomainFlowHandler(config_entries.ConfigFlow):
    """Handle a domain config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        super().__init__()

    async def async_step_user(self, user_input=None):
        """Handle a flow start."""
        _LOGGER.debug(f"Starting async_step_user of {DEFAULT_NAME}")

        errors = None

        if user_input is not None:
            try:
                config_manager = ConfigManager(self.hass, None)
                config_manager.update_credentials(user_input)

                await config_manager.initialize()

                api = RestAPI(self.hass, config_manager)

                await api.validate()

                if api.status == ConnectivityStatus.Connected:
                    _LOGGER.debug("User inputs are valid")

                    user_input[CONF_PASSWORD] = config_manager.password_hashed

                    return self.async_create_entry(title=DEFAULT_NAME, data=user_input)

                else:
                    _LOGGER.warning("Failed to create integration")

                    errors = {"base": ConnectivityStatus.get_ha_error(api.status)}

            except LoginError:
                errors = {"base": "invalid_admin_credentials"}

            if errors is not None:
                error_message = errors.get("base")

                _LOGGER.warning(f"Failed to create integration, Error: {error_message}")
        else:
            user_input = {}

        new_user_input = {
            vol.Optional(CONF_HOST, default=user_input.get(CONF_HOST)): str,
            vol.Optional(CONF_PATH, default=user_input.get(CONF_PATH, "/")): str,
            vol.Optional(
                CONF_PORT, default=user_input.get(CONF_PORT, DEFAULT_PORT)
            ): int,
            vol.Optional(CONF_SSL, default=user_input.get(CONF_SSL, False)): bool,
            vol.Optional(CONF_USERNAME, default=user_input.get(CONF_USERNAME)): str,
            vol.Optional(CONF_PASSWORD, default=user_input.get(CONF_PASSWORD)): str,
        }

        schema = vol.Schema(new_user_input)

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
