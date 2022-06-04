from __future__ import annotations

from typing import Any, Callable

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry

from ...core.helpers.const import *


class ConfigData:
    name: str
    host: str
    port: int
    ssl: bool
    path: str
    use_original_stream: bool
    username: str | None
    password: str | None
    password_clear_text: str | None
    entry: ConfigEntry | None

    def __init__(self):
        self.name = DEFAULT_NAME
        self.host = ""
        self.port = DEFAULT_PORT
        self.ssl = False
        self.path = ""
        self.username = None
        self.password = None
        self.password_clear_text = None
        self.use_original_stream = False
        self.entry = None

    @property
    def has_credentials(self):
        has_username = self.username and len(self.username) > 0
        has_password = self.password_clear_text and len(self.password_clear_text) > 0

        has_credentials = has_username or has_password

        return has_credentials

    def get_fields(self) -> dict[vol.Marker, Any]:
        fields = {
            vol.Optional(CONF_HOST, default=self.host): str,
            vol.Optional(CONF_PATH, default=self.path): str,
            vol.Optional(CONF_PORT, default=self.port): int,
            vol.Optional(CONF_SSL, default=self.ssl): bool,
            vol.Optional(CONF_USERNAME, default=self.username): str,
            vol.Optional(CONF_PASSWORD, default=self.password_clear_text): str,
            vol.Optional(CONF_USE_ORIGINAL_STREAM, default=self.use_original_stream): bool,
        }

        return fields

    def __repr__(self):
        obj = {
            CONF_NAME: self.name,
            CONF_HOST: self.host,
            CONF_PORT: self.port,
            CONF_SSL: self.ssl,
            CONF_PATH: self.path,
            CONF_USERNAME: self.username,
            CONF_PASSWORD: self.password,
            CONF_USE_ORIGINAL_STREAM: self.use_original_stream
        }

        to_string = f"{obj}"

        return to_string


def get_config_data_from_entry_data(data: dict, password_getter: Callable[[dict], str]) -> ConfigData:
    result = ConfigData()

    if data is not None:
        result.host = data.get(CONF_HOST)
        result.port = data.get(CONF_PORT, 8080)
        result.ssl = data.get(CONF_SSL, False)
        result.path = data.get(CONF_PATH, "")

        result.username = data.get(CONF_USERNAME)
        result.password = data.get(CONF_PASSWORD)
        result.password_clear_text = password_getter(data)

        result.use_original_stream = data.get(CONF_USE_ORIGINAL_STREAM, False)

    return result


def get_config_data_from_entry(entry: ConfigEntry, password_getter: Callable[[dict], str]) -> ConfigData:
    data = entry.data

    result = get_config_data_from_entry_data(data, password_getter)
    result.entry = entry

    return result
