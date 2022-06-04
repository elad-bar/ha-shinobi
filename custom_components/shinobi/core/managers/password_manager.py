from __future__ import annotations

import logging
from os import path, remove

from cryptography.fernet import Fernet

from homeassistant.core import HomeAssistant

from ...core.helpers.const import *
from ...core.models.storage_data import StorageData
from .storage_manager import StorageManager

_LOGGER = logging.getLogger(__name__)


async def async_get_password_manager(hass: HomeAssistant) -> PasswordManager:
    data = hass.data.get(DATA)

    if data is None or PASSWORD_MANAGER not in data:
        password_manager = PasswordManager(hass)
        await password_manager.initialize()

        if data is not None:
            hass.data[DATA][PASSWORD_MANAGER] = password_manager

    else:
        password_manager: PasswordManager = hass.data[DATA][PASSWORD_MANAGER]

    return password_manager


class PasswordManager:
    data: StorageData | None
    hass: HomeAssistant
    crypto: Fernet

    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self.data = None

    async def initialize(self):
        if self.data is None:
            storage_manager = StorageManager(self.hass)

            self.data = await storage_manager.async_load_from_store()

            if self.data.key is None:
                legacy_key_path = self.hass.config.path(DOMAIN_KEY_FILE)

                if path.exists(legacy_key_path):
                    with open(legacy_key_path, "rb") as file:
                        self.data.key = file.read().decode("utf-8")

                    remove(legacy_key_path)
                else:
                    self.data.key = Fernet.generate_key().decode("utf-8")

                await storage_manager.async_save_to_store(self.data)

            self.crypto = Fernet(self.data.key.encode())

    def set(self, data: dict) -> None:
        user_password = data.get(CONF_PASSWORD)

        if user_password is not None:
            encrypted = self.crypto.encrypt(user_password.encode()).decode()

            data[CONF_PASSWORD] = encrypted

    def get(self, data: dict) -> str:
        password = data.get(CONF_PASSWORD)

        if password is not None and len(password) > 0:
            password = self.crypto.decrypt(password.encode()).decode()

        return password
