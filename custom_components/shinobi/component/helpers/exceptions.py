from homeassistant.exceptions import HomeAssistantError

from ...core.helpers.enums import ConnectivityStatus


class APIValidationException(HomeAssistantError):
    endpoint: str
    status: ConnectivityStatus

    def __init__(self, endpoint: str, status: ConnectivityStatus):
        super().__init__(f"API cannot process request to '{endpoint}', Status: {status}")

        self.endpoint = endpoint
        self.status = status
