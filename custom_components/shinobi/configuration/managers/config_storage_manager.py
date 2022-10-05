"""Storage handlers."""
import logging

from homeassistant.helpers.json import JSONEncoder
from homeassistant.helpers.storage import Store

from ...core.helpers.const import *
from ..models.local_config import LocalConfig

_LOGGER = logging.getLogger(__name__)


class ConfigurationStorageManager:
    def __init__(self, hass):
        self._hass = hass

    @property
    def file_name(self):
        file_name = f"{DOMAIN}.config.json"

        return file_name

    async def async_load_from_store(self) -> LocalConfig:
        """Load the retained data from store and return de-serialized data."""
        store = Store(self._hass, STORAGE_VERSION, self.file_name, encoder=JSONEncoder)

        data = await store.async_load()

        result = LocalConfig.from_dict(data)

        return result

    async def async_save_to_store(self, data: LocalConfig):
        """Generate dynamic data to store and save it to the filesystem."""
        store = Store(self._hass, STORAGE_VERSION, self.file_name, encoder=JSONEncoder)

        await store.async_save(data.to_dict())
