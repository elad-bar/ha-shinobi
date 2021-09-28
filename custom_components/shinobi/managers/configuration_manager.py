import logging

from homeassistant.config_entries import ConfigEntry

from ..helpers.const import *
from ..models.config_data import ConfigData
from .password_manager import PasswordManager

_LOGGER = logging.getLogger(__name__)


class ConfigManager:
    data: ConfigData
    config_entry: ConfigEntry
    password_manager: PasswordManager

    def __init__(self, password_manager: PasswordManager):
        self.password_manager = password_manager

    async def update(self, config_entry: ConfigEntry):
        data = config_entry.data

        result: ConfigData = await self.get_basic_data(data)

        self.config_entry = config_entry
        self.data = result

    async def get_basic_data(self, data):
        _LOGGER.debug(f"get_basic_data, data: {data}")

        result = ConfigData()

        if data is not None:
            result.host = data.get(CONF_HOST)
            result.port = data.get(CONF_PORT, 8080)
            result.ssl = data.get(CONF_SSL, False)
            result.path = data.get(CONF_PATH, "")

            result.username = data.get(CONF_USERNAME)
            result.password = data.get(CONF_PASSWORD)

            if result.password is not None and len(result.password) > 0:
                password_clear_text = await self.password_manager.decrypt(
                    result.password
                )

                result.password_clear_text = password_clear_text
            else:
                result.password_clear_text = result.password

        return result
