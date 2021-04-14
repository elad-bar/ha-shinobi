import json
import logging
from datetime import datetime
from typing import Optional

from homeassistant.components.mqtt import Message, async_subscribe
from homeassistant.core import callback, HomeAssistant

from custom_components.shinobi.api.shinobi_api import ShinobiApi
from custom_components.shinobi.helpers.const import *

_LOGGER = logging.getLogger(__name__)


def _get_camera_binary_sensor_key(topic, event_type):
    key = f"{topic}_{event_type}".lower()

    return key


class MQTTManager:
    remove_subscription = None
    hass: Optional[HomeAssistant] = None
    message_handler = None
    mqtt_states: dict
    api: ShinobiApi

    def __init__(self, hass: HomeAssistant, api: ShinobiApi, event_handler):
        self.remove_subscription = None
        self.hass = hass
        self.event_handler = event_handler
        self.mqtt_states = {}
        self.api = api

    @property
    def is_supported(self) -> bool:
        return DATA_MQTT in self.hass.data

    async def initialize(self):
        """Subscribe MQTT events."""
        self.terminate()

        mqtt_topic = f"{MQTT_ALL_TOPIC}/{self.api.group_id}/#"

        _LOGGER.info(
            f"Subscribing to MQTT topics '{mqtt_topic}', QOS: {DEFAULT_QOS}"
        )

        @callback
        def state_message_received(message: Message):
            """Handle a new received MQTT state message."""
            _LOGGER.debug(
                f"Received Shinobi Video Message - {message.topic}: {message.payload}"
            )

            self._state_message_received(message)

        self.remove_subscription = await async_subscribe(
            self.hass, mqtt_topic, state_message_received, DEFAULT_QOS
        )

    def terminate(self):
        if self.remove_subscription is not None:
            self.remove_subscription()
            self.remove_subscription = None

    def _state_message_received(self, message: Message):
        topic = message.topic
        payload = json.loads(message.payload)

        trigger_name = payload.get(TRIGGER_NAME)
        trigger_details = payload.get(TRIGGER_DETAILS, {})
        trigger_plug = trigger_details.get(TRIGGER_DETAILS_PLUG)
        trigger_reason = trigger_details.get(TRIGGER_DETAILS_REASON)
        trigger_matrices = trigger_details.get(TRIGGER_DETAILS_MATRICES, [])

        trigger_tags = []

        for trigger_object in trigger_matrices:
            trigger_tag = trigger_object.get(TRIGGER_DETAILS_MATRICES_TAG)

            if trigger_tag not in trigger_tags:
                trigger_tags.append(trigger_tag)

        value = {
            TRIGGER_NAME: trigger_name,
            TRIGGER_DETAILS_REASON: trigger_reason,
            TRIGGER_TAGS: trigger_tags,
            TRIGGER_STATE: STATE_ON,
            TRIGGER_TIMESTAMP: datetime.now().timestamp()
        }

        _LOGGER.debug(f"Topic: {topic} for {trigger_plug}: {value}")

        self.set_state(topic, trigger_plug, value)
        self.event_handler()

    def get_state(self, topic, event_type):
        key = _get_camera_binary_sensor_key(topic, event_type)

        state = self.mqtt_states.get(key, TRIGGER_DEFAULT)

        return state

    def set_state(self, topic, event_type, value):
        key = _get_camera_binary_sensor_key(topic, event_type)

        self.mqtt_states[key] = value
