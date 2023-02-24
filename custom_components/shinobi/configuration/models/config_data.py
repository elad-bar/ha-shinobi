from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PATH,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
)

from ..helpers.const import DEFAULT_PORT


class ConfigData:
    host: str | None
    port: int
    ssl: bool
    path: str
    username: str | None
    password: str | None
    entry: ConfigEntry | None

    def __init__(self):
        self.host = None
        self.port = DEFAULT_PORT
        self.ssl = False
        self.path = ""
        self.username = None
        self.password = None
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

        return result

    def to_dict(self):
        obj = {
            CONF_HOST: self.host,
            CONF_PORT: self.port,
            CONF_SSL: self.ssl,
            CONF_PATH: self.path,
            CONF_USERNAME: self.username,
            CONF_PASSWORD: self.password,
        }

        return obj

    def __repr__(self):
        to_string = f"{self.to_dict()}"

        return to_string
