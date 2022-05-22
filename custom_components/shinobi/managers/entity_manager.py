import datetime
import logging
import sys
from typing import Dict, List, Optional

from homeassistant.core import HomeAssistant
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

                    _LOGGER.info(f"{entities_count} {domain} components created")

            deleted_count = len(entities_to_delete.keys())
            if deleted_count > 0:
                for entity_id in entities_to_delete:
                    entity = entities_to_delete[entity_id]

                    await self._handle_deleted_entities(entity_id, entity)

                _LOGGER.info(f"{deleted_count} components deleted")

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

            self._load_switch_entity(monitor, BinarySensorDeviceClass.SOUND, device)
            self._load_switch_entity(monitor, BinarySensorDeviceClass.MOTION, device)

    def _load_camera_component(self, monitor: MonitorData, device: str):
        try:
            entity_name = f"{self.integration_title} {monitor.name}"

            if monitor.jpeg_api_enabled:
                use_original_stream = self.config_data.use_original_stream

                snapshot = self.api.build_url(monitor.snapshot)

                stream_source = None

                if not use_original_stream:
                    for stream in monitor.streams:
                        if stream is not None:
                            stream_source = self.api.build_url(stream)
                            break

                if use_original_stream or stream_source is None:
                    stream_source = monitor.original_stream

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
                created = entity is None

                if created:
                    entity = EntityData()

                    entity.id = monitor.id
                    entity.name = entity_name
                    entity.icon = DEFAULT_ICON
                    entity.domain = DOMAIN_CAMERA

                data = {
                    "state": (entity.state, monitor.mode),
                    "attributes": (entity.attributes, attributes),
                    "device_name": (entity.device_name, device)
                }

                if created or self._compare_data(entity, data):
                    entity.state = monitor.mode
                    entity.attributes = attributes
                    entity.device_name = device

                    entity.status = ENTITY_STATUS_CREATED if created else ENTITY_STATUS_UPDATED

                self._set_entity(entity, [monitor.disabled])

            else:
                _LOGGER.warning(f"JPEG API is not enabled for {monitor.name}, Monitor will not be created")

        except Exception as ex:
            self.log_exception(ex, f"Failed to load camera for {monitor}")

    def _load_select_component(self, monitor: MonitorData, device: str):
        try:
            entity_name = f"{self.integration_title} {monitor.name} {ATTR_MONITOR_MODE}"

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name,
            }

            entity = self.get_entity(DOMAIN_SELECT, entity_name)
            created = entity is None

            if created:
                entity = EntityData()

                entity.id = monitor.id
                entity.name = entity_name
                entity.attributes = attributes
                entity.icon = DEFAULT_ICON
                entity.domain = DOMAIN_SELECT

            data = {
                "state": (entity.state, monitor.mode),
                "device_name": (entity.device_name, device),
            }

            if created or self._compare_data(entity, data):
                entity.device_name = device
                entity.state = monitor.mode

                entity.status = ENTITY_STATUS_CREATED if created else ENTITY_STATUS_UPDATED

            self._set_entity(entity)

        except Exception as ex:
            self.log_exception(ex, f"Failed to load select for {monitor}")

    def _load_binary_sensor_entity(
            self,
            monitor: MonitorData,
            sensor_type: BinarySensorDeviceClass,
            device: str
    ):
        try:
            entity_name = f"{self.integration_title} {monitor.name} {sensor_type.capitalize()}"

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
            created = entity is None

            is_sound = sensor_type == BinarySensorDeviceClass.SOUND
            detector_active = monitor.has_audio_detector if is_sound else monitor.has_motion_detector

            if created:
                entity = EntityData()

                entity.id = monitor.id
                entity.name = entity_name
                entity.icon = DEFAULT_ICON
                entity.binary_sensor_device_class = sensor_type
                entity.domain = DOMAIN_BINARY_SENSOR

            data = {
                "state": (entity.state, str(state)),
                "attributes": (entity.attributes, attributes),
                "device_name": (entity.device_name, device),
            }

            if created or self._compare_data(entity, data):
                entity.state = state
                entity.attributes = attributes
                entity.device_name = device

                entity.status = ENTITY_STATUS_CREATED if created else ENTITY_STATUS_UPDATED

            self._set_entity(entity, [monitor.disabled, not detector_active])

        except Exception as ex:
            self.log_exception(
                ex, f"Failed to load binary sensor for {monitor.name}"
            )

    def _load_switch_entity(
            self,
            monitor: MonitorData,
            sensor_type: BinarySensorDeviceClass,
            device: str
    ):
        try:
            entity_name = f"{self.integration_title} {monitor.name} {sensor_type.capitalize()}"

            state = monitor.has_motion_detector \
                if sensor_type == BinarySensorDeviceClass.MOTION \
                else monitor.has_audio_detector

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name
            }

            entity = self.get_entity(DOMAIN_SWITCH, entity_name)
            created = entity is None

            is_sound = sensor_type == BinarySensorDeviceClass.SOUND

            if created:
                entity = EntityData()

                entity.id = monitor.id
                entity.name = entity_name
                entity.icon = DEFAULT_ICON
                entity.binary_sensor_device_class = sensor_type
                entity.domain = DOMAIN_SWITCH

            data = {
                "state": (entity.state, str(state)),
                "attributes": (entity.attributes, attributes),
                "device_name": (entity.device_name, device),
            }

            if created or self._compare_data(entity, data):
                entity.state = str(state)
                entity.attributes = attributes
                entity.device_name = device

                entity.status = ENTITY_STATUS_CREATED if created else ENTITY_STATUS_UPDATED

            self._set_entity(entity, [monitor.disabled, is_sound and not monitor.has_audio])
        except Exception as ex:
            self.log_exception(
                ex, f"Failed to load switch for {monitor.name}"
            )

    @staticmethod
    def _compare_data(entity: EntityData, data: dict[str, tuple]) -> bool:
        modified = False
        msgs = []

        for data_key in data:
            original, latest = data[data_key]

            if original != latest:
                msgs.append(f"{data_key} changed from {original} to {latest}")
                modified = True

        if modified:
            full_message = " | ".join(msgs)

            _LOGGER.debug(f"{entity.name} | {entity.domain} | {full_message}")

        return modified

    def _set_entity(
            self,
            entity: EntityData,
            destructors: list[bool] = None
    ):
        try:
            if destructors is not None and True in destructors:
                if entity.status == ENTITY_STATUS_CREATED:
                    entity = None

                else:
                    entity.status = ENTITY_STATUS_DELETED

            if entity is not None:
                self._check_domain(entity.domain)

                self._entities[entity.domain][entity.name] = entity

                if entity.status != ENTITY_STATUS_READY:
                    _LOGGER.debug(f"{entity.name} ({entity.domain}) {entity.status}, state: {entity.state}")

        except Exception as ex:
            self.log_exception(
                ex, f"Failed to set entity, domain: {entity.domain}, name: {entity.name}"
            )

    async def async_set_monitor_mode(self, monitor_id: str, mode: str):
        await self.api.async_set_monitor_mode(monitor_id, mode)

        await self._ha.async_update(datetime.datetime.now)

    async def async_set_motion_detection(self, monitor_id: str, enabled: bool):
        await self.api.async_set_motion_detection(monitor_id, enabled)

        await self._ha.async_update(datetime.datetime.now)

    async def async_set_sound_detection(self, monitor_id: str, enabled: bool):
        await self.api.async_set_sound_detection(monitor_id, enabled)

        await self._ha.async_update(datetime.datetime.now)

    @staticmethod
    def log_exception(ex, message):
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno

        _LOGGER.error(f"{message}, Error: {str(ex)}, Line: {line_number}")
