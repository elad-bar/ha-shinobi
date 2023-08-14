import json
import logging
import sys

from cryptography.fernet import InvalidToken

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.config_entries import STORAGE_VERSION, ConfigEntry
from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import translation
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.json import JSONEncoder
from homeassistant.helpers.storage import Store

from ..common.consts import (
    CONFIGURATION_FILE,
    DATA_KEY_EVENT_DURATION,
    DATA_KEY_ORIGINAL_STREAM,
    DATA_KEY_PROXY_RECORDINGS,
    DEFAULT_ENTRY_ID,
    DEFAULT_NAME,
    DOMAIN,
    INVALID_TOKEN_SECTION,
    SENSOR_AUTO_OFF_MOTION,
    SENSOR_AUTO_OFF_SOUND,
)
from ..common.entity_descriptions import IntegrationEntityDescription
from ..models.config_data import ConfigData

_LOGGER = logging.getLogger(__name__)


class ConfigManager:
    _data: dict | None
    _config_data: ConfigData

    _store: Store | None
    _translations: dict | None
    _password: str | None
    _entry_title: str
    _entry_id: str

    _is_set_up_mode: bool
    _is_initialized: bool

    def __init__(self, hass: HomeAssistant | None, entry: ConfigEntry | None = None):
        self._hass = hass
        self._entry = entry
        self._entry_id = DEFAULT_ENTRY_ID if entry is None else entry.entry_id
        self._entry_title = DEFAULT_NAME if entry is None else entry.title

        self._config_data = ConfigData()

        self._data = None

        self._store = None
        self._translations = None

        self._is_set_up_mode = entry is None
        self._is_initialized = False

        if hass is not None:
            self._store = Store(
                hass, STORAGE_VERSION, CONFIGURATION_FILE, encoder=JSONEncoder
            )

    @property
    def is_initialized(self) -> bool:
        is_initialized = self._is_initialized

        return is_initialized

    @property
    def entry_id(self) -> str:
        entry_id = self._entry_id

        return entry_id

    @property
    def entry_title(self) -> str:
        entry_title = self._entry_title

        return entry_title

    @property
    def entry(self) -> ConfigEntry:
        entry = self._entry

        return entry

    @property
    def use_original_stream(self):
        use_original_stream = self._data.get(DATA_KEY_ORIGINAL_STREAM, False)

        return use_original_stream

    @property
    def use_proxy_for_recordings(self):
        use_original_stream = self._data.get(DATA_KEY_PROXY_RECORDINGS, False)

        return use_original_stream

    @property
    def event_duration(self):
        event_duration = self._data.get(DATA_KEY_EVENT_DURATION, {})

        return event_duration

    @property
    def config_data(self) -> ConfigData:
        config_data = self._config_data

        return config_data

    async def initialize(self, entry_config: dict):
        try:
            await self._load()

            self._config_data.update(entry_config)

            if self._hass is None:
                self._translations = {}

            else:
                self._translations = await translation.async_get_translations(
                    self._hass, self._hass.config.language, "entity", {DOMAIN}
                )

            _LOGGER.debug(
                f"Translations loaded, Data: {json.dumps(self._translations)}"
            )

            self._is_initialized = True

        except InvalidToken:
            self._is_initialized = False

            _LOGGER.error(
                f"Invalid encryption key, Please follow instructions in {INVALID_TOKEN_SECTION}"
            )

        except Exception as ex:
            self._is_initialized = False

            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to initialize configuration manager, Error: {ex}, Line: {line_number}"
            )

    def get_translation(
        self,
        platform: Platform,
        entity_key: str,
        attribute: str,
        default_value: str | None = None,
    ) -> str | None:
        translation_key = (
            f"component.{DOMAIN}.entity.{platform}.{entity_key}.{attribute}"
        )

        translated_value = self._translations.get(translation_key, default_value)

        _LOGGER.debug(
            "Translations requested, "
            f"Key: {translation_key}, "
            f"Default value: {default_value}, "
            f"Value: {translated_value}"
        )

        return translated_value

    def get_entity_name(
        self,
        entity_description: IntegrationEntityDescription,
        device_info: DeviceInfo,
    ) -> str:
        entity_key = entity_description.key

        device_name = device_info.get("name")
        platform = entity_description.platform

        translated_name = self.get_translation(
            platform, entity_key, CONF_NAME, entity_description.name
        )

        entity_name = (
            device_name
            if translated_name is None or translated_name == ""
            else f"{device_name} {translated_name}"
        )

        return entity_name

    def get_event_duration(self, event_type: BinarySensorDeviceClass) -> int:
        event_duration = self.event_duration.get(
            event_type, SENSOR_AUTO_OFF_MOTION.total_seconds()
        )

        return event_duration

    async def update_event_duration(
        self, event_type: BinarySensorDeviceClass, interval: int
    ):
        _LOGGER.debug(f"Set event duration for {event_type} to {interval} seconds")

        if DATA_KEY_EVENT_DURATION not in self._data:
            self._data[DATA_KEY_EVENT_DURATION] = {}

        self._data[DATA_KEY_EVENT_DURATION][event_type] = interval

        await self._save()

    async def update_original_stream(self, is_on: bool):
        _LOGGER.debug(f"Set use original stream to {is_on}")

        self._data[DATA_KEY_ORIGINAL_STREAM] = is_on

        await self._save()

    async def update_proxy_for_recordings(self, is_on: bool):
        _LOGGER.debug(f"Set proxy for recordings to {is_on}")

        self._data[DATA_KEY_PROXY_RECORDINGS] = is_on

        await self._save()

    def get_debug_data(self) -> dict:
        data = self._config_data.to_dict()

        for key in self._data:
            data[key] = self._data[key]

        return data

    async def _load(self):
        self._data = None

        await self._load_config_from_file()

        if self._data is None:
            self._data = {}

        default_configuration = self._get_defaults()

        for key in default_configuration:
            value = default_configuration[key]

            if key not in self._data:
                self._data[key] = value

        await self._save()

    @staticmethod
    def _get_defaults() -> dict:
        data = {
            DATA_KEY_ORIGINAL_STREAM: False,
            DATA_KEY_PROXY_RECORDINGS: False,
            DATA_KEY_EVENT_DURATION: {
                BinarySensorDeviceClass.MOTION: SENSOR_AUTO_OFF_MOTION.total_seconds(),
                BinarySensorDeviceClass.SOUND: SENSOR_AUTO_OFF_SOUND.total_seconds(),
            },
        }

        return data

    async def _load_config_from_file(self):
        if self._store is not None:
            store_data = await self._store.async_load()

            if store_data is not None:
                self._data = store_data.get(self._entry_id)

    async def remove(self, entry_id: str):
        if self._store is None:
            return

        store_data = await self._store.async_load()

        if store_data is not None and entry_id in store_data:
            data = {key: store_data[key] for key in store_data}
            data.pop(entry_id)

            await self._store.async_save(data)

    async def _save(self):
        if self._store is None:
            return

        should_save = False
        store_data = await self._store.async_load()

        if store_data is None:
            store_data = {}

        entry_data = store_data.get(self._entry_id, {})

        _LOGGER.debug(
            f"Storing config data: {json.dumps(self._data)}, "
            f"Exiting: {json.dumps(entry_data)}"
        )

        for key in self._data:
            stored_value = entry_data.get(key)

            if key in [CONF_PASSWORD, CONF_USERNAME]:
                entry_data.pop(key)

                if stored_value is not None:
                    should_save = True

            else:
                current_value = self._data.get(key)

                if stored_value != current_value:
                    should_save = True

                    entry_data[key] = self._data[key]

        if should_save and self._entry_id != DEFAULT_ENTRY_ID:
            if DEFAULT_ENTRY_ID in store_data:
                store_data.pop(DEFAULT_ENTRY_ID)

            store_data[self._entry_id] = entry_data

            await self._store.async_save(store_data)
