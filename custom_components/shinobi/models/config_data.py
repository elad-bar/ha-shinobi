from typing import Optional

from ..helpers.const import *


class ConfigData:
    name: str
    host: str
    port: int
    ssl: bool
    path: str
    username: Optional[str]
    password: Optional[str]
    password_clear_text: Optional[str]

    def __init__(self):
        self.name = DEFAULT_NAME
        self.host = ""
        self.port = DEFAULT_PORT
        self.ssl = False
        self.path = ""
        self.username = None
        self.password = None
        self.password_clear_text = None

    @property
    def protocol(self):
        protocol = PROTOCOLS[self.ssl]

        return protocol

    @property
    def ws_protocol(self):
        protocol = WS_PROTOCOLS[self.ssl]

        return protocol

    @property
    def api_url(self):
        path = "/" if self.path == "" else self.path

        url = (
            f"{self.protocol}://{self.host}:{self.port}{path}"
        )

        return url

    @property
    def ws_url(self):
        path = "/" if self.path == "" else self.path

        url = (
            f"{self.ws_protocol}://{self.host}:{self.port}{path}{SHINOBI_WS_ENDPOINT}"
        )

        return url

    @property
    def has_credentials(self):
        has_username = self.username and len(self.username) > 0
        has_password = self.password_clear_text and len(self.password_clear_text) > 0

        has_credentials = has_username or has_password

        return has_credentials

    def __repr__(self):
        obj = {
            CONF_NAME: self.name,
            CONF_HOST: self.host,
            CONF_PORT: self.port,
            CONF_SSL: self.ssl,
            CONF_PATH: self.path,
            CONF_USERNAME: self.username,
            CONF_PASSWORD: self.password
        }

        to_string = f"{obj}"

        return to_string
