from custom_components.shinobi.common.connectivity_status import ConnectivityStatus
from homeassistant.exceptions import HomeAssistantError


class LoginError(Exception):
    def __init__(self):
        self.error = "Failed to login"


class AlreadyExistsError(HomeAssistantError):
    title: str

    def __init__(self, title: str):
        self.title = title


class APIValidationException(HomeAssistantError):
    endpoint: str
    status: ConnectivityStatus

    def __init__(self, endpoint: str, status: ConnectivityStatus):
        super().__init__(
            f"API cannot process request to '{endpoint}', Status: {status}"
        )

        self.endpoint = endpoint
        self.status = status
