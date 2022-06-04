from custom_components.shinobi.component.helpers.enums import ConnectivityStatus
from homeassistant.exceptions import HomeAssistantError


class MonitorNotFoundError(HomeAssistantError):
    monitor_id: str

    def __init__(self, monitor_id: str):
        self.monitor_id = monitor_id


class AlreadyExistsError(HomeAssistantError):
    title: str

    def __init__(self, title: str):
        self.title = title


class LoginError(HomeAssistantError):
    errors: dict

    def __init__(self, errors):
        self.errors = errors


class APIRequestException(Exception):
    endpoint: str
    response: dict

    def __init__(self, endpoint, response):
        super().__init__(f"API Request failed")

        self.endpoint = endpoint
        self.response = response


class APIValidationException(Exception):
    endpoint: str
    status: ConnectivityStatus

    def __init__(self, endpoint: str, status: ConnectivityStatus):
        super().__init__(f"API cannot process request to '{endpoint}', Status: {status}")

        self.endpoint = endpoint
        self.status = status
