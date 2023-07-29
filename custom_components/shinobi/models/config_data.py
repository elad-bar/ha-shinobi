import voluptuous as vol
from voluptuous import Schema

from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PATH,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
)

from ..common.consts import (
    CONF_TITLE,
    DEFAULT_NAME,
    DEFAULT_PORT,
    PROTOCOLS,
    WS_PROTOCOLS,
)

DATA_KEYS = [CONF_HOST, CONF_PORT, CONF_SSL, CONF_PATH, CONF_USERNAME, CONF_PASSWORD]


class ConfigData:
    _hostname: str | None
    _port: int
    _is_ssl: bool
    _api_path: str | None
    _username: str | None
    _password: str | None

    def __init__(self):
        self._hostname = None
        self._port = DEFAULT_PORT
        self._is_ssl = False
        self._api_path = None
        self._username = None
        self._password = None

    @property
    def hostname(self) -> str:
        hostname = self._hostname

        return hostname

    @property
    def port(self) -> int:
        port = self._port

        return port

    @property
    def ssl(self) -> bool:
        ssl = self._is_ssl

        return ssl

    @property
    def path(self) -> str | None:
        api_path = self._api_path

        return api_path

    @property
    def username(self) -> str:
        username = self._username

        return username

    @property
    def password(self) -> str:
        password = self._password

        return password

    @property
    def ws_url(self):
        protocol = WS_PROTOCOLS[self._is_ssl]

        url_path = "/" if self._api_path == "" else self._api_path

        url = f"{protocol}://{self._hostname}:{self._port}{url_path}"

        return url

    @property
    def api_url(self):
        protocol = PROTOCOLS[self._is_ssl]

        url_path = "/" if self._api_path == "" else self._api_path

        url = f"{protocol}://{self._hostname}:{self._port}{url_path}"

        return url

    def update(self, data: dict):
        self._password = data.get(CONF_PASSWORD)
        self._username = data.get(CONF_USERNAME)
        self._api_path = data.get(CONF_PATH)
        self._hostname = data.get(CONF_HOST)
        self._port = data.get(CONF_PORT)
        self._is_ssl = data.get(CONF_SSL)

    def to_dict(self):
        obj = {
            CONF_USERNAME: self.username,
            CONF_PATH: self.path,
            CONF_HOST: self.hostname,
            CONF_PORT: self.port,
            CONF_SSL: self.ssl,
        }

        return obj

    def __repr__(self):
        to_string = f"{self.to_dict()}"

        return to_string

    @staticmethod
    def default_schema(user_input: dict | None) -> Schema:
        if user_input is None:
            user_input = {}

        new_user_input = {
            vol.Required(
                CONF_TITLE, default=user_input.get(CONF_TITLE, DEFAULT_NAME)
            ): str,
            vol.Required(CONF_HOST, default=user_input.get(CONF_HOST)): str,
            vol.Required(CONF_PATH, default=user_input.get(CONF_PATH, "/")): str,
            vol.Required(
                CONF_PORT, default=user_input.get(CONF_PORT, DEFAULT_PORT)
            ): int,
            vol.Optional(CONF_SSL, default=user_input.get(CONF_SSL, False)): bool,
            vol.Required(CONF_USERNAME, default=user_input.get(CONF_USERNAME)): str,
            vol.Required(CONF_PASSWORD, default=user_input.get(CONF_PASSWORD)): str,
        }

        schema = vol.Schema(new_user_input)

        return schema
