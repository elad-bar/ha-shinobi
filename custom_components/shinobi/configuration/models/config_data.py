from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry

from ...configuration.helpers.const import *


class ConfigData:
    name: str
    host: str | None
    port: int
    ssl: bool
    path: str
    use_original_stream: bool
    username: str | None
    password: str | None
    entry: ConfigEntry | None

    def __init__(self):
        self.name = DEFAULT_NAME
        self.host = None
        self.port = DEFAULT_PORT
        self.ssl = False
        self.path = ""
        self.username = None
        self.password = None
        self.use_original_stream = False
        self.entry = None

    @staticmethod
    def from_dict(data: dict[str, Any] = None) -> ConfigData:
        result = ConfigData()

        if data is not None:
            result.host = data.get(CONF_HOST)
            result.port = data.get(CONF_PORT, DEFAULT_PORT)
            result.ssl = data.get(CONF_SSL, False)
            result.path = data.get(CONF_PATH, "")

            result.username = data.get(CONF_USERNAME)
            result.password = data.get(CONF_PASSWORD)

            result.use_original_stream = data.get(CONF_USE_ORIGINAL_STREAM, False)

        return result

    def to_dict(self):
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

        return obj

    def __repr__(self):
        to_string = f"{self.to_dict()}"

        return to_string
