from homeassistant.exceptions import HomeAssistantError


class CameraNotFoundError(HomeAssistantError):
    camera_id: str

    def __init__(self, camera_id: str):
        self.camera_id = camera_id


class AlreadyExistsError(HomeAssistantError):
    title: str

    def __init__(self, title: str):
        self.title = title


class LoginError(HomeAssistantError):
    errors: dict

    def __init__(self, errors):
        self.errors = errors
