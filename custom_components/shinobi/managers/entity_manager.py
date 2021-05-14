import logging
import sys
from typing import Dict, List, Optional

from homeassistant.components.camera import DEFAULT_CONTENT_TYPE
from homeassistant.components.stream import DOMAIN as DOMAIN_STREAM
from homeassistant.const import CONF_AUTHENTICATION
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_registry import EntityRegistry

from ..api.shinobi_api import ShinobiApi
from ..helpers.const import *
from ..models.camera_data import CameraData
from ..models.config_data import ConfigData
from ..models.entity_data import EntityData
from .configuration_manager import ConfigManager
from .device_manager import DeviceManager
from .mqtt_manager import MQTTManager

_LOGGER = logging.getLogger(__name__)


class EntityManager:
    hass: HomeAssistant
    ha = None
    entities: dict
    domain_component_manager: dict

    def __init__(self, hass, ha):
        self.hass = hass
        self.ha = ha
        self.domain_component_manager = {}
        self.entities = {}

    @property
    def entity_registry(self) -> EntityRegistry:
        return self.ha.entity_registry

    @property
    def config_data(self) -> ConfigData:
        return self.ha.config_data

    @property
    def config_manager(self) -> ConfigManager:
        return self.ha.config_manager

    @property
    def api(self) -> ShinobiApi:
        return self.ha.api

    @property
    def mqtt_client(self) -> MQTTManager:
        return self.ha.mqtt_manager

    @property
    def device_manager(self) -> DeviceManager:
        return self.ha.device_manager

    @property
    def mqtt_manager(self) -> MQTTManager:
        return self.ha.mqtt_manager

    @property
    def integration_title(self) -> str:
        return self.config_manager.config_entry.title

    def set_domain_component(self, domain, async_add_entities, component):
        self.domain_component_manager[domain] = {
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
        for domain in self.entities:
            for name in self.entities[domain]:
                entity = self.entities[domain][name]

                entities.append(entity)

        return entities

    def check_domain(self, domain):
        if domain not in self.entities:
            self.entities[domain] = {}

    def get_entities(self, domain) -> Dict[str, EntityData]:
        self.check_domain(domain)

        return self.entities[domain]

    def get_entity(self, domain, name) -> Optional[EntityData]:
        entities = self.get_entities(domain)
        entity = entities.get(name)

        return entity

    def get_entity_status(self, domain, name):
        entity = self.get_entity(domain, name)

        status = ENTITY_STATUS_EMPTY if entity is None else entity.status

        return status

    def set_entity_status(self, domain, name, status):
        if domain in self.entities and name in self.entities[domain]:
            self.entities[domain][name].status = status

    def delete_entity(self, domain, name):
        if domain in self.entities and name in self.entities[domain]:
            del self.entities[domain][name]

    def set_entity(self, domain, name, data: EntityData):
        try:
            self.check_domain(domain)

            self.entities[domain][name] = data
        except Exception as ex:
            self.log_exception(
                ex, f"Failed to set_entity, domain: {domain}, name: {name}"
            )

    def create_components(self):
        available_camera = self.api.camera_list

        mqtt_binary_sensors = []

        for camera in available_camera:
            self.generate_camera_component(camera)

            if self.mqtt_manager.is_supported:
                current_mqtt_binary_sensors = self.generate_camera_binary_sensors(camera)

                mqtt_binary_sensors.extend(current_mqtt_binary_sensors)

    def update(self):
        self.hass.async_create_task(self._async_update())

    async def _async_update(self):
        step = "Mark as ignore"
        try:
            entities_to_delete = []

            for entity in self.get_all_entities():
                entities_to_delete.append(entity.unique_id)

            step = "Create components"

            self.create_components()

            step = "Start updating"

            for domain in SIGNALS:
                step = f"Start updating domain {domain}"

                entities_to_add = []
                domain_component_manager = self.domain_component_manager[domain]
                domain_component = domain_component_manager["component"]
                async_add_entities = domain_component_manager["async_add_entities"]

                entities = dict(self.get_entities(domain))

                for entity_key in entities:
                    step = f"Start updating {domain} -> {entity_key}"

                    entity = entities[entity_key]

                    entity_id = self.entity_registry.async_get_entity_id(
                        domain, DOMAIN, entity.unique_id
                    )

                    if entity.status == ENTITY_STATUS_CREATED:
                        entity_item = self.entity_registry.async_get(entity_id)

                        if entity.unique_id in entities_to_delete:
                            entities_to_delete.remove(entity.unique_id)

                        step = f"Mark as created - {domain} -> {entity_key}"

                        entity_component = domain_component(
                            self.hass, self.config_manager.config_entry.entry_id, entity
                        )

                        if entity_id is not None:
                            entity_component.entity_id = entity_id

                            state = self.hass.states.get(entity_id)

                            if state is None:
                                restored = True
                            else:
                                restored = state.attributes.get("restored", False)

                                if restored:
                                    _LOGGER.info(
                                        f"Entity {entity.name} restored | {entity_id}"
                                    )

                            if restored:
                                if entity_item is None or not entity_item.disabled:
                                    entities_to_add.append(entity_component)
                        else:
                            entities_to_add.append(entity_component)

                        entity.status = ENTITY_STATUS_READY

                        if entity_item is not None:
                            entity.disabled = entity_item.disabled

                step = f"Add entities to {domain}"

                if len(entities_to_add) > 0:
                    async_add_entities(entities_to_add, True)

            if len(entities_to_delete) > 0:
                _LOGGER.info(f"Following items will be deleted: {entities_to_delete}")

                for domain in SIGNALS:
                    entities = dict(self.get_entities(domain))

                    for entity_key in entities:
                        entity = entities[entity_key]
                        if entity.unique_id in entities_to_delete:
                            await self.ha.delete_entity(domain, entity.name)

        except Exception as ex:
            self.log_exception(ex, f"Failed to update, step: {step}")

    def get_camera_entity(self, camera: CameraData, sensor_type) -> EntityData:
        entity = None

        try:
            device_name = self.device_manager.get_camera_device_name(camera)

            entity_name = f"{self.integration_title} {camera.name} {sensor_type.capitalize()}"
            unique_id = f"{DOMAIN}-{DOMAIN_BINARY_SENSOR}-{entity_name}"

            state_topic = f"{MQTT_ALL_TOPIC}/{self.api.group_id}/{camera.monitorId}/trigger"

            mqtt_state = TRIGGER_DEFAULT

            if self.mqtt_manager is not None:
                mqtt_state = self.mqtt_manager.get_state(state_topic, sensor_type)

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name
            }

            for attr in BINARY_SENSOR_ATTRIBUTES:
                if attr in mqtt_state:
                    attributes[attr] = mqtt_state.get(attr)

            entity = EntityData()

            entity.id = camera.monitorId
            entity.unique_id = unique_id
            entity.name = entity_name
            entity.state = mqtt_state.get(TRIGGER_STATE)
            entity.attributes = attributes
            entity.icon = DEFAULT_ICON
            entity.device_name = device_name
            entity.topic = state_topic
            entity.event = sensor_type
            entity.device_class = sensor_type
            entity.type = sensor_type

            self.mqtt_manager.set_state(state_topic, sensor_type, mqtt_state)

            self.set_entity(DOMAIN_BINARY_SENSOR, entity_name, entity)
        except Exception as ex:
            self.log_exception(
                ex, f"Failed to get camera for {camera.name}"
            )

        return entity

    def generate_camera_binary_sensors(self, camera: CameraData):
        entities = []

        try:
            supported_sensors = []
            audio_event = SENSOR_DEVICE_CLASS[TRIGGER_PLUG_DB]
            motion_event = SENSOR_DEVICE_CLASS[TRIGGER_PLUG_YOLO]

            if camera.has_audio and camera.has_audio_detector:
                supported_sensors.append(audio_event)

            if camera.has_motion_detector:
                supported_sensors.append(motion_event)

            for sensor_type_name in supported_sensors:
                entity = self.get_camera_entity(camera, sensor_type_name)

                entities.append(entity)

        except Exception as ex:
            self.log_exception(ex, f"Failed to generate binary sensors for {camera}")

        return entities

    def get_camera_component(self, camera: CameraData) -> EntityData:
        entity = None
        try:
            device_name = self.device_manager.get_camera_device_name(camera)

            entity_name = f"{self.integration_title} {camera.name}"
            username = self.config_data.username
            password = self.config_data.password_clear_text
            base_url = self.api.base_url

            unique_id = f"{DOMAIN}-{DOMAIN_CAMERA}-{entity_name}"

            snapshot = f"{base_url}{camera.snapshot}"
            still_image_url_template = cv.template(snapshot)

            support_stream = DOMAIN_STREAM in self.hass.data

            stream_source = ""

            for stream in camera.streams:
                stream_source = f"{base_url}{stream}"

                break

            camera_details = {
                CONF_NAME: f"{entity_name}",
                CONF_STILL_IMAGE_URL: still_image_url_template,
                CONF_STREAM_SOURCE: stream_source,
                CONF_LIMIT_REFETCH_TO_URL_CHANGE: False,
                CONF_FRAMERATE: camera.fps,
                CONF_CONTENT_TYPE: DEFAULT_CONTENT_TYPE,
                CONF_VERIFY_SSL: False,
                CONF_USERNAME: username,
                CONF_PASSWORD: password,
                CONF_AUTHENTICATION: AUTHENTICATION_BASIC,
                CONF_SUPPORT_STREAM: support_stream,
            }

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name,
                CONF_STREAM_SOURCE: stream_source,
                CONF_STILL_IMAGE_URL: snapshot
            }

            for key in CAMERA_ATTRIBUTES:
                key_name = CAMERA_ATTRIBUTES[key]
                attributes[key_name] = camera.details.get(key, "N/A")

            monitor_details = camera.details.get("details", {})

            for key in CAMERA_DETAILS_ATTRIBUTES:
                key_name = CAMERA_DETAILS_ATTRIBUTES[key]
                attributes[key_name] = monitor_details.get(key, "N/A")

            entity = EntityData()

            entity.id = camera.monitorId
            entity.unique_id = unique_id
            entity.name = entity_name
            entity.attributes = attributes
            entity.icon = DEFAULT_ICON
            entity.device_name = device_name
            entity.details = camera_details
            entity.state = camera.status

        except Exception as ex:
            self.log_exception(ex, f"Failed to get camera for {camera}")

        return entity

    def generate_camera_component(self, camera: CameraData):
        try:
            entity = self.get_camera_component(camera)

            if entity is not None:
                self.set_entity(DOMAIN_CAMERA, entity.name, entity)

        except Exception as ex:
            self.log_exception(ex, f"Failed to generate camera for {camera}")

    @staticmethod
    def log_exception(ex, message):
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno

        _LOGGER.error(f"{message}, Error: {str(ex)}, Line: {line_number}")
