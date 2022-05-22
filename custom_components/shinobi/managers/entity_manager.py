import datetime
import logging
import sys
from typing import Dict, List, Optional

from homeassistant.components.camera import DEFAULT_CONTENT_TYPE
from homeassistant.components.stream import DOMAIN as DOMAIN_STREAM
from homeassistant.const import CONF_AUTHENTICATION
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_registry import EntityRegistry, RegistryEntryDisabler

from ..api.shinobi_api import ShinobiApi
from ..helpers.const import *
from ..models.config_data import ConfigData
from ..models.entity_data import EntityData
from ..models.monitor_data import MonitorData
from .configuration_manager import ConfigManager
from .device_manager import DeviceManager
from .event_manager import EventManager

_LOGGER = logging.getLogger(__name__)


class EntityManager:
    hass: HomeAssistant

    def __init__(self, hass, ha):
        self.hass: HomeAssistant = hass
        self._ha = ha
        self._domain_component_manager: dict = {}
        self._entities: dict = {}

    @property
    def entity_registry(self) -> EntityRegistry:
        return self._ha.entity_registry

    @property
    def config_data(self) -> ConfigData:
        return self._ha.config_data

    @property
    def config_manager(self) -> ConfigManager:
        return self._ha.config_manager

    @property
    def api(self) -> ShinobiApi:
        return self._ha.api

    @property
    def device_manager(self) -> DeviceManager:
        return self._ha.device_manager

    @property
    def event_manager(self) -> EventManager:
        return self._ha.event_manager

    @property
    def integration_title(self) -> str:
        return self.config_manager.config_entry.title

    def set_domain_component(self, domain, async_add_entities, component):
        self._domain_component_manager[domain] = {
            "async_add_entities": async_add_entities,
            "component": component,
        }

    def is_device_name_in_use(self, device_name):
        result = False

        for entity in self.get_all_entities():
            if entity.device_name == device_name:
                result = True
                break

        return result

    def get_all_entities(self) -> List[EntityData]:
        entities = []
        for domain in self._entities:
            for name in self._entities[domain]:
                entity = self._entities[domain][name]

                entities.append(entity)

        return entities

    def _check_domain(self, domain):
        if domain not in self._entities:
            self._entities[domain] = {}

    def _get_entities(self, domain) -> Dict[str, EntityData]:
        self._check_domain(domain)

        return self._entities[domain]

    def get_entity(self, domain, name) -> Optional[EntityData]:
        entities = self._get_entities(domain)
        entity = entities.get(name)

        return entity

    def delete_entity(self, domain, name):
        if domain in self._entities and name in self._entities[domain]:
            del self._entities[domain][name]

    def update(self):
        self.hass.async_create_task(self._async_update())

    async def _handle_created_entities(self, entity_id, entity: EntityData, domain_component):
        entity_item = self.entity_registry.async_get(entity_id)

        if entity_item is not None:
            if entity.disabled:
                _LOGGER.info(f"Disabling entity, Data: {entity}")

                self.entity_registry.async_update_entity(entity_id,
                                                         disabled_by=RegistryEntryDisabler.INTEGRATION)

            else:
                entity.disabled = entity_item.disabled

        entity_component = domain_component(
            self.hass,
            self.config_manager.config_entry.entry_id,
            entity
        )

        if entity_id is not None:
            entity_component.entity_id = entity_id
            state = self.hass.states.get(entity_id)

            if state is not None:
                restored = state.attributes.get("restored", False)

                if restored:
                    _LOGGER.info(f"Restored {entity_id} ({entity.name})")

        entity.status = ENTITY_STATUS_READY

        return entity_component

    async def _handle_deleted_entities(self, entity_id: str, entity: EntityData):
        entity_item = self.entity_registry.async_get(entity_id)

        if entity_item is not None:
            _LOGGER.info(f"Removed {entity_id} ({entity.name})")

            self.entity_registry.async_remove(entity_id)

        self.delete_entity(entity.domain, entity.name)

    async def _async_update(self):
        _LOGGER.debug("Starting to update entities")

        try:
            entities_to_delete = {}

            self._create_components()

            for domain in self._entities:
                entities_to_add = []
                domain_entities = self._entities[domain]

                domain_component_manager = self._domain_component_manager[domain]
                domain_component = domain_component_manager["component"]
                async_add_entities = domain_component_manager["async_add_entities"]

                for entity_key in domain_entities:
                    entity = domain_entities[entity_key]

                    entity_id = self.entity_registry.async_get_entity_id(
                        domain, DOMAIN, entity.unique_id
                    )

                    if entity.status == ENTITY_STATUS_CREATED:
                        entity_component = await self._handle_created_entities(entity_id, entity, domain_component)

                        if entity_component is not None:
                            entities_to_add.append(entity_component)

                    elif entity.status == ENTITY_STATUS_DELETED:
                        entities_to_delete[entity_id] = entity

                entities_count = len(entities_to_add)

                if entities_count > 0:
                    async_add_entities(entities_to_add)

                    _LOGGER.info(f"{entities_count} were added for {domain}")

            if len(entities_to_delete.keys()) > 0:
                for entity_id in entities_to_delete:
                    entity = entities_to_delete[entity_id]

                    await self._handle_deleted_entities(entity_id, entity)

                _LOGGER.info(f"{entities_to_delete.keys()} were deleted")

        except Exception as ex:
            self.log_exception(ex, "Failed to update")

    def _create_components(self):
        _LOGGER.debug("Creating components")

        for monitor_id in self.api.monitors:
            monitor = self.api.monitors.get(monitor_id)
            device = self.device_manager.get_monitor_device_name(monitor.id)

            self._load_camera_component(monitor, device)
            self._load_select_component(monitor, device)

            self._load_binary_sensor_entity(monitor, BinarySensorDeviceClass.SOUND, device)
            self._load_binary_sensor_entity(monitor, BinarySensorDeviceClass.MOTION, device)

    def _load_camera_component(self, monitor: MonitorData, device: str):
        try:
            entity_name = f"{self.integration_title} {monitor.name}"

            if monitor.jpeg_api_enabled:
                username = self.config_data.username
                password = self.config_data.password_clear_text
                use_original_stream = self.config_data.use_original_stream

                unique_id = f"{DOMAIN}-{DOMAIN_CAMERA}-{entity_name}"

                snapshot = self.api.build_url(monitor.snapshot)
                still_image_url_template = cv.template(snapshot)

                support_stream = DOMAIN_STREAM in self.hass.data

                stream_source = None

                if not use_original_stream:
                    for stream in monitor.streams:
                        if stream is not None:
                            stream_source = self.api.build_url(stream)
                            break

                if use_original_stream or stream_source is None:
                    stream_source = monitor.original_stream

                entity_details = {
                    CONF_NAME: f"{entity_name}",
                    CONF_STILL_IMAGE_URL: still_image_url_template,
                    CONF_STREAM_SOURCE: stream_source,
                    CONF_LIMIT_REFETCH_TO_URL_CHANGE: False,
                    CONF_FRAMERATE: monitor.fps,
                    CONF_CONTENT_TYPE: DEFAULT_CONTENT_TYPE,
                    CONF_VERIFY_SSL: False,
                    CONF_USERNAME: username,
                    CONF_PASSWORD: password,
                    CONF_AUTHENTICATION: AUTHENTICATION_BASIC,
                    CONF_SUPPORT_STREAM: support_stream,
                    CONF_MOTION_DETECTION: monitor.has_motion_detector
                }

                attributes = {
                    ATTR_FRIENDLY_NAME: entity_name,
                    CONF_STREAM_SOURCE: stream_source,
                    CONF_STILL_IMAGE_URL: snapshot
                }

                for key in MONITOR_ATTRIBUTES:
                    key_name = MONITOR_ATTRIBUTES[key]
                    attributes[key_name] = monitor.details.get(key, "N/A")

                monitor_details = monitor.details.get(ATTR_MONITOR_DETAILS, {})

                for key in MONITOR_DETAILS_ATTRIBUTES:
                    key_name = MONITOR_DETAILS_ATTRIBUTES[key]
                    attributes[key_name] = monitor_details.get(key, "N/A")

                entity = self.get_entity(DOMAIN_CAMERA, entity_name)
                create = entity is None
                modified = False

                if create:
                    entity = EntityData()

                    entity.id = monitor.id
                    entity.unique_id = unique_id
                    entity.name = entity_name
                    entity.icon = DEFAULT_ICON
                    entity.domain = DOMAIN_CAMERA

                if entity.state != monitor.mode \
                        or entity.attributes != attributes \
                        or entity.device_name != device \
                        or entity.details != entity_details:

                    entity.state = monitor.mode
                    entity.attributes = attributes
                    entity.device_name = device
                    entity.details = entity_details

                    modified = True

                self._set_entity(entity, monitor, create, modified)

            else:
                _LOGGER.warning(f"JPEG API is not enabled for {monitor.name}, Monitor will not be created")

        except Exception as ex:
            self.log_exception(ex, f"Failed to get monitor for {monitor}")

    def _load_select_component(self, monitor: MonitorData, device: str):
        try:
            entity_name = f"{self.integration_title} {monitor.name} {ATTR_MONITOR_MODE}"

            unique_id = f"{DOMAIN}-{DOMAIN_SELECT}-{entity_name}"

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name,
            }

            entity = self.get_entity(DOMAIN_SELECT, entity_name)
            create = entity is None
            modified = False

            if entity is None:
                entity = EntityData()

                entity.id = monitor.id
                entity.unique_id = unique_id
                entity.name = entity_name
                entity.attributes = attributes
                entity.icon = DEFAULT_ICON
                entity.domain = DOMAIN_SELECT

            if entity.state != monitor.mode or entity.device_name != device:
                entity.device_name = device
                entity.state = monitor.mode

                modified = True

            self._set_entity(entity, monitor, create, modified, True)

        except Exception as ex:
            self.log_exception(ex, f"Failed to get select for {monitor}")

    def _load_binary_sensor_entity(
            self,
            monitor: MonitorData,
            sensor_type: BinarySensorDeviceClass,
            device: str
    ):
        try:
            entity_name = f"{self.integration_title} {monitor.name} {sensor_type.capitalize()}"
            unique_id = f"{DOMAIN}-{DOMAIN_BINARY_SENSOR}-{entity_name}"

            state_topic = f"{self.api.group_id}/{monitor.id}"

            state = STATE_OFF
            event_state = TRIGGER_DEFAULT

            if self.event_manager is not None:
                event_state = self.event_manager.get_state(state_topic, sensor_type)
                state = event_state.get(TRIGGER_STATE, STATE_OFF)

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name
            }

            for attr in BINARY_SENSOR_ATTRIBUTES:
                if attr in event_state:
                    attributes[attr] = event_state.get(attr)

            entity = self.get_entity(DOMAIN_BINARY_SENSOR, entity_name)
            create = entity is None
            modified = False

            if create:
                entity = EntityData()

                entity.id = monitor.id
                entity.unique_id = unique_id
                entity.name = entity_name
                entity.icon = DEFAULT_ICON
                entity.binary_sensor_device_class = sensor_type
                entity.domain = DOMAIN_BINARY_SENSOR

            if entity.state != state or entity.attributes != attributes or entity.device_name != device:
                entity.state = state
                entity.attributes = attributes
                entity.device_name = device

                modified = True

            self._set_entity(entity, monitor, create, modified)
        except Exception as ex:
            self.log_exception(
                ex, f"Failed to get monitor for {monitor.name}"
            )

    def _set_entity(
            self,
            entity: EntityData,
            monitor: MonitorData,
            created: bool,
            modified: bool,
            ignore_monitor_state: bool = False
    ):
        try:
            if created:
                entity.status = ENTITY_STATUS_CREATED

            if not created and modified:
                entity.status = ENTITY_STATUS_UPDATED

            disabled = not ignore_monitor_state and monitor.disabled

            if not disabled \
                    and entity.domain == DOMAIN_BINARY_SENSOR \
                    and not monitor.is_sensor_active(entity.binary_sensor_device_class):

                disabled = True

            if disabled:
                entity.status = ENTITY_STATUS_DELETED

            self._check_domain(entity.domain)

            self._entities[entity.domain][entity.name] = entity

            if entity.status != ENTITY_STATUS_READY:
                _LOGGER.debug(f"{entity.name} {entity.status}, state: {entity.state}")

        except Exception as ex:
            self.log_exception(
                ex, f"Failed to set entity, domain: {entity.domain}, name: {entity.name}"
            )

    async def async_set_monitor_mode(self, monitor_id: str, mode: str):
        await self.api.async_set_monitor_mode(monitor_id, mode)

        await self._ha.async_update(datetime.datetime.now)

    async def async_set_motion_detection(self, monitor_id: str, motion_detection_enabled: bool):
        await self.api.async_set_motion_detection(monitor_id, motion_detection_enabled)

        await self._ha.async_update(datetime.datetime.now)

    @staticmethod
    def log_exception(ex, message):
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno

        _LOGGER.error(f"{message}, Error: {str(ex)}, Line: {line_number}")
